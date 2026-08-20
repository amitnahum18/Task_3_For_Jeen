from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.pool import StaticPool

from lfx.custom.custom_component.component import Component
from lfx.io import (
    IntInput,
    Output,
    SecretStrInput,
    StrInput,
)
from lfx.schema.message import Message

ALLOWED_PRIORITY = {"High", "Medium", "Low"}
ALLOWED_STATUS = {"Open", "In Progress", "Closed", "Escalated"}


class SecureSupportQueryTool(Component):
    display_name = "Support Requests Query Tool (Parameterized)"
    description = (
        "Looks up rows in support_requests using structured filters (category, priority, "
        "status, customer name, email). The agent never writes SQL text — every filter "
        "value is bound as a query parameter, so there is no SQL-injection surface "
        "regardless of what is passed in. Leave any filter empty to match all values for it."
    )
    name = "SecureSupportQueryTool"
    icon = "LangChain"

    inputs = [
        StrInput(
            name="db_host",
            display_name="DB Host",
            info="Bind to a Global Variable, e.g. SUPPORT_DB_HOST.",
            required=True,
        ),
        IntInput(
            name="db_port",
            display_name="DB Port",
            info="Bind to a Global Variable, e.g. SUPPORT_DB_PORT.",
            value=5432,
            required=True,
        ),
        StrInput(
            name="db_name",
            display_name="DB Name",
            info="Bind to a Global Variable, e.g. SUPPORT_DB_NAME.",
            required=True,
        ),
        StrInput(
            name="db_user",
            display_name="DB User",
            info="Bind to a Global Variable, e.g. SUPPORT_DB_USER.",
            required=True,
        ),
        SecretStrInput(
            name="db_password",
            display_name="DB Password",
            info=(
                "Bind to a Global Variable, e.g. SUPPORT_DB_PASSWORD. Kept separate from "
                "the other connection fields (rather than one URI string) so the password "
                "is never concatenated into a DSN by hand — SQLAlchemy's URL builder "
                "handles encoding, so special characters in the password can't break "
                "parsing or leak into logs/error messages."
            ),
            required=True,
        ),
        StrInput(
            name="category",
            display_name="Category filter",
            info="Exact category, e.g. 'Billing'. Leave empty to match any category.",
            tool_mode=True,
        ),
        StrInput(
            name="priority",
            display_name="Priority filter",
            info="One of: High, Medium, Low. Leave empty to match any priority.",
            tool_mode=True,
        ),
        StrInput(
            name="ticket_status",
            display_name="Status filter",
            info="One of: Open, In Progress, Closed, Escalated. Leave empty to match any status.",
            tool_mode=True,
        ),
        StrInput(
            name="customer_name",
            display_name="Customer name filter",
            info="Partial, case-insensitive match. Leave empty to match any customer.",
            tool_mode=True,
        ),
        StrInput(
            name="email",
            display_name="Email filter",
            info="Exact customer email. Leave empty to match any email.",
            tool_mode=True,
        ),
        IntInput(
            name="max_rows",
            display_name="Max Rows",
            info="Hard cap on rows returned. Fixed by the flow, not controllable by the agent.",
            value=50,
        ),
    ]

    outputs = [
        Output(display_name="Result", name="result", method="run_query"),
    ]

    def _clean(self, value: str | None) -> str | None:
        value = (value or "").strip()
        return value or None

    def _build_engine(self):
        url = URL.create(
            drivername="postgresql",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port or 5432,
            database=self.db_name,
        )
        return create_engine(url, poolclass=StaticPool)

    def _with_filters(self, applied: dict, body: str) -> Message:
        """Prefix any returned message with the filters actually used, so the
        single Result output always carries both what was searched for and
        what came back."""
        filters_text = ", ".join(f"{k}={v}" for k, v in applied.items()) or "none (unfiltered)"
        return Message(text=f"Filters: {filters_text}\n\n{body}")

    def run_query(self) -> Message:
        category = self._clean(self.category)
        priority = self._clean(self.priority)
        ticket_status = self._clean(self.ticket_status)
        customer_name = self._clean(self.customer_name)
        email = self._clean(self.email)

        applied = {
            k: v
            for k, v in (
                ("category", category),
                ("priority", priority),
                ("status", ticket_status),
                ("customer_name", customer_name),
                ("email", email),
            )
            if v
        }

        if priority and priority not in ALLOWED_PRIORITY:
            return self._with_filters(
                applied, f"Query rejected: priority must be one of {sorted(ALLOWED_PRIORITY)}, got '{priority}'."
            )
        if ticket_status and ticket_status not in ALLOWED_STATUS:
            return self._with_filters(
                applied, f"Query rejected: status must be one of {sorted(ALLOWED_STATUS)}, got '{ticket_status}'."
            )

        conditions = []
        params: dict = {}

        if category:
            conditions.append("category = :category")
            params["category"] = category
        if priority:
            conditions.append("priority = :priority")
            params["priority"] = priority
        if ticket_status:
            conditions.append("status = :status")
            params["status"] = ticket_status
        if customer_name:
            conditions.append("customer_name ILIKE :customer_name")
            params["customer_name"] = f"%{customer_name}%"
        if email:
            conditions.append("email = :email")
            params["email"] = email

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        # limit is our own bounded int, never caller-supplied text, so inlining it is safe —
        # every filter value above goes through a bound :param instead of string concatenation.
        limit = max(1, min(self.max_rows or 50, 200))
        sql = (
            "SELECT id, customer_name, email, category, priority, status, created_at "
            f"FROM support_requests {where_clause} "
            "ORDER BY created_at DESC "
            f"LIMIT {limit}"
        )

        try:
            engine = self._build_engine()
        except Exception as exc:  # noqa: BLE001 - surfaced to the agent as tool output
            return self._with_filters(applied, f"Could not connect to the database: {exc}")

        try:
            with engine.connect() as connection:
                if engine.dialect.name == "postgresql":
                    connection = connection.execution_options(postgresql_readonly=True)
                with connection.begin() as transaction:
                    result = connection.execute(text(sql), params)
                    rows = result.fetchall()
                    columns = list(result.keys())
                    transaction.rollback()  # never persist, even for a SELECT
        except Exception as exc:  # noqa: BLE001 - surfaced to the agent as tool output
            return self._with_filters(applied, f"Query failed: {exc}")

        if not rows:
            return self._with_filters(applied, "No records found matching these filters.")

        lines = [" | ".join(columns)]
        lines += [" | ".join(str(v) for v in row) for row in rows]
        return self._with_filters(applied, f"{len(rows)} row(s) returned\n" + "\n".join(lines))
