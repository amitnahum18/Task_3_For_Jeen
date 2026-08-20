# Task 3 – Multi-Agent Flow ב-Langflow (Jeen AI – Home Assignment)

מערכת תמיכת לקוחות מבוססת 3 סוכנים ב-Langflow, עם ניתוב דינמי (לא כל הודעה מפעילה את כל הסוכנים/הכלים) ושני Tools: שאילתת SQL מאובטחת ל-PostgreSQL ושליחת מייל דרך Gmail.

## תוכן העניינים
- [ארכיטקטורה](#ארכיטקטורה)
- [קבצים בריפו](#קבצים-בריפו)
- [הרצה מקומית עם Docker](#הרצה-מקומית-עם-docker)
- [ייבוא ה-Flow ל-Langflow](#ייבוא-ה-flow-ל-langflow)
- [Global Variables ב-Langflow](#global-variables-ב-langflow)
- [משתני סביבה (.env)](#משתני-סביבה-env)
- [בדיקות (Testing)](#בדיקות-testing)
- [טיפול בשגיאות](#טיפול-בשגיאות)
- [וידאו הדגמה](#וידאו-הדגמה)

## ארכיטקטורה

שלושה Agents, כל אחד עם אחריות נפרדת וברורה:

1. **Orchestrator Agent** (`BooleanRouterAgent`, ראו [custom_components/boolean_router_agent.py](custom_components/boolean_router_agent.py)) —
   מבין את כוונת המשתמש ומחליט בין שתי צורות תגובה בלבד:
   - **FORM 2 – מענה ישיר**: ברכות, small talk, שאלות כלליות על המערכת, ניסיונות prompt injection — עונה בעצמו, בלי לגעת ב-Analysis/Response ובלי להפעיל Tools.
   - **FORM 1 – ROUTE**: בקשה אמיתית (מידע, אימייל, סטטוס) — מעביר את הקונטקסט הלאה ל-Analysis Agent.

   מומש כרכיב מותאם אישית שיורש מ-`AgentComponent` המובנה של Langflow ומוסיף ענף True/False (בדומה ל-If/Else), כך שההחלטה עצמה נשלטת לגמרי דרך ה-System Prompt (Agent Instructions) של הסוכן, לא הארד-קוד ברכיב.

2. **Analysis Agent** — שולף מידע דרך ה-SQL Tool (read-only), מזהה מידע חסר (למשל בקשה בלי שם/אימייל/מספר פנייה — ואז לא שולף מה-DB בכלל), מסווג דחיפות (Low/Med/High/Critical), ומחזיר פלט מובנה: `שם/אימייל | קטגוריה וסטטוס | דחיפות | פעולה מומלצת`.

3. **Response Agent** — מנסח את התשובה הסופית ללקוח על בסיס פלט ה-Analysis, ומפעיל את Gmail Tool **רק** אם המשתמש ביקש מפורשות לקבל עדכון במייל.

**Tools:**
- **Support Requests Query Tool** (`SecureSupportQueryTool`, ראו [custom_components/sql_secure_query_tool.py](custom_components/sql_secure_query_tool.py)) — הסוכן אף פעם לא כותב SQL בעצמו; הוא מעביר פילטרים מובנים (category / priority / status / customer_name / email) שנקשרים כפרמטרים מוכנים (parameterized query), כך שאין משטח ל-SQL injection. השאילתה read-only (`postgresql_readonly=True` + rollback תמיד, גם ל-SELECT).
- **Gmail Send Tool** (`GmailSendToolComponent`, ראו [custom_components/gmail_send_tool.py](custom_components/gmail_send_tool.py)) — שולח מייל טקסט פשוט דרך Gmail SMTP/STARTTLS, עם ולידציה לכתובת הנמען ודחייה של ניסיונות header-injection (CR/LF בכתובת/בנושא).

## קבצים בריפו

| קובץ/תיקייה | תיאור |
|---|---|
| [Task 3 Agents.json](<Task 3 Agents.json>) | ה-Flow המלא, מיוצא מ-Langflow (ייבוא ישיר דרך Import) |
| [custom_components/](custom_components/) | 3 הרכיבים המותאמים אישית (Orchestrator router, SQL tool, Gmail tool) |
| [db/init/](db/init/) | סקריפטים ליצירת `support_db` והזנת נתוני הדוגמה, רצים אוטומטית בהפעלה הראשונה של ה-container |
| [docker-compose.yml](docker-compose.yml) | Langflow + Postgres להרצה מקומית |
| [test_plan.md](test_plan.md) | תוכנית בדיקות מלאה לכל אחד מ-3 הסוכנים (תרחישי קלט + התנהגות רצויה) |
| [run_tests.py](run_tests.py) | מריץ את תרחישי הבדיקה מול ה-Flow החי דרך HTTP POST וכותב את [results.md](results.md) |
| [results.md](results.md) | תוצאות ריצה בפועל של תרחישי הבדיקה |

> קובץ הווידאו של ההדגמה (`Task_3.mp4`, ~137MB) לא נכלל בריפו — ראו [וידאו הדגמה](#וידאו-הדגמה).

## הרצה מקומית עם Docker

```bash
cp .env.example .env   # למלא LANGFLOW_SUPERUSER / LANGFLOW_SUPERUSER_PASSWORD
docker-compose up -d
```

- Langflow: http://localhost:7860
- Postgres: localhost:5432 (משתמש: `langflow`, סיסמה: `langflow`)

### שמירת נתונים
שני ה-volumes (`langflow_data`, `postgres_data`) מחזיקים את הנתונים על הדיסק. עצירה והפעלה מחדש לא מוחקות כלום:
```bash
docker-compose stop
docker-compose start
```
מחיקה מלאה (כולל הנתונים) רק אם תרצו לאפס הכל:
```bash
docker-compose down -v
```

### מסדי הנתונים
ה-container של Postgres מחזיק שני DBs נפרדים:
- `langflow_meta` — משמש את Langflow עצמו לשמירת ה-Flows וההיסטוריה.
- `support_db` — נוצר אוטומטית מ-[db/init/01_create_support_requests.sql](db/init/01_create_support_requests.sql) בהפעלה הראשונה בלבד, ומכיל את טבלת `support_requests` עם נתוני הדוגמה מהמטלה (בתוספת נתונים מדומים נוספים מ-[db/init/02_seed_fake_data.sql](db/init/02_seed_fake_data.sql) לצורך בדיקות אגרגציה/ספירה).

> הסקריפטים ב-`db/init` רצים **פעם אחת בלבד**, כשה-volume של Postgres ריק (הפעלה ראשונה). אם תרצו להריץ אותם מחדש, צריך קודם `docker-compose down -v` (מוחק את הנתונים) ואז `docker-compose up -d`.

## ייבוא ה-Flow ל-Langflow

1. פתחו את Langflow (http://localhost:7860), צרו Flow חדש → **Import** → בחרו את [`Task 3 Agents.json`](<Task 3 Agents.json>).
2. שני הרכיבים המותאמים (`SecureSupportQueryTool`, `GmailSendTool`) וה-Orchestrator (`BooleanRouterAgent`) נטענים אוטומטית מ-[custom_components/](custom_components/) אם התיקייה מוגדרת כ-Custom Components Path של Langflow (`LANGFLOW_COMPONENTS_PATH`), או שניתן להעתיק את הקבצים ידנית ל-`~/.langflow/components`.
3. הגדירו את ה-Global Variables (ראו סעיף הבא) ולאחר מכן קשרו אותם לשדות המתאימים ברכיבי ה-Tools בתוך ה-Flow (SQL Tool / Gmail Tool).

## Global Variables ב-Langflow

אין לשים מפתחות/סיסמאות בתוך ה-Flow עצמו. יש להגדיר אותם דרך **Settings → Global Variables** בממשק של Langflow, ולהצביע אליהם מתוך רכיבי ה-Agent/Tool:

| Global Variable | משמש את | הערה |
|---|---|---|
| `SUPPORT_DB_HOST` | Support Requests Query Tool | לדוגמה `postgres` (מתוך רשת ה-Docker הפנימית) |
| `SUPPORT_DB_PORT` | Support Requests Query Tool | `5432` |
| `SUPPORT_DB_NAME` | Support Requests Query Tool | `support_db` |
| `SUPPORT_DB_USER` | Support Requests Query Tool | `langflow` |
| `SUPPORT_DB_PASSWORD` | Support Requests Query Tool | Secret — סיסמת ה-DB |
| `GMAIL_ADDRESS` | Gmail Send Tool | כתובת השולח |
| `GMAIL_APP_PASSWORD` | Gmail Send Tool | Secret — App Password בן 16 תווים (דורש 2-Step Verification בחשבון הגוגל, לא סיסמת החשבון הרגילה) |

חיבור ה-SQL Tool מתוך רשת ה-Docker הפנימית של Langflow:
```
postgresql://langflow:langflow@postgres:5432/support_db
```
להתחברות מהמחשב עצמו (למשל DBeaver/pgAdmin לבדיקה ידנית):
```
postgresql://langflow:langflow@localhost:5432/support_db
```

## משתני סביבה (.env)

קובץ `.env` (לא מסונכרן ל-Git — ראו [.env.example](.env.example)) משמש רק את הקבצים בריפו הזה (docker-compose ו-`run_tests.py`), ונפרד לגמרי מה-Global Variables של Langflow עצמו:

| משתנה | שימוש |
|---|---|
| `LANGFLOW_SUPERUSER` / `LANGFLOW_SUPERUSER_PASSWORD` | משתמש האדמין של Langflow (`LANGFLOW_AUTO_LOGIN=false` ב-[docker-compose.yml](docker-compose.yml)) |
| `LANGFLOW_API_KEY` | מפתח API של Langflow, בשימוש `run_tests.py` להרצת הבדיקות מול ה-Flow |
| `LANGFLOW_FLOW_URL` | כתובת ה-`/api/v1/run/<flow-id>` של ה-Flow המיובא |

## בדיקות (Testing)

[test_plan.md](test_plan.md) מפרט תרחישי בדיקה לכל אחד משלושת הסוכנים (ניתוב נכון ב-Orchestrator, שימוש נכון ב-Tools ב-Analysis, ניסוח והפעלת Gmail נכונה ב-Response), כולל מקרי קצה: prompt injection, בקשת מחיקה (הכלי read-only), לקוח לא קיים, כשל חיבור/כלי, ריבוי שאלות בהודעה אחת.

הרצה מול ה-Flow החי (Playground או HTTP POST):
```bash
python run_tests.py
```
מריץ את כל התרחישים ב-[test_plan.md](test_plan.md) דרך HTTP POST מול `LANGFLOW_FLOW_URL`, וכותב את הפלט ל-[results.md](results.md).

## טיפול בשגיאות

- **מידע חסר** (Analysis) — אם אין שם/אימייל/מספר פנייה מזוהה, לא מתבצעת שאילתה ל-DB כלל; המערכת מבקשת פרטים מזהים.
- **פנייה לא נמצאה** — מוחזר `Record Not Found` במקום להמציא נתונים; דחיפות מסווגת Med (לא Low, כי הסיכון לא ידוע).
- **שגיאת כלי/חיבור ל-DB** — ה-SQL Tool מחזיר הודעת שגיאה מפורשת (`Could not connect...` / `Query failed...`) שמובחנת מ"לא נמצא"; מטופלת בנפרד ("Data Unavailable — Tool Error") ולא מוצגת כהצלחה מדומה.
- **בקשות שינוי/מחיקה** — ה-SQL Tool read-only בלבד (rollback תמיד, גם אחרי SELECT); ניסיון UPDATE/DELETE נדחה ברמת הכלי, והסוכן מדווח שלא ניתן לבצע שינוי.
- **כשל שליחת מייל** — Gmail Tool מבחין בין כתובת לא תקינה, כשל אימות (SMTPAuthenticationError), סירוב נמען (SMTPRecipientsRefused) וכשל חיבור כללי; בכל מקרה מחזיר הודעת כשל מפורשת, וה-Response Agent לא מתחזה שהמייל נשלח.
- **בקשה לא ברורה / הודעה ריקה** — Orchestrator עונה ישירות ומבקש הבהרה, בלי לנתב הלאה ובלי להפעיל Tools.
- **Prompt injection** — Orchestrator מזהה וסירוב מנומס, בלי לחשוף system prompt/שמות כלים פנימיים, ובלי ניתוב הלאה.

## וידאו הדגמה

קובץ הווידאו (`Task_3.mp4`, 2–5 דקות, ~137MB) חורג ממגבלת הגודל של GitHub (100MB לקובץ) ולכן אינו חלק מהריפו. הוא כלול בהגשה בנפרד (Google Drive) ומדגים: הצגת ה-Flow ותפקידי הסוכנים, שיחה של 6–7 הודעות, איך מתקבלות ההחלטות וזזה מידע בין הסוכנים, הפעלת ה-Tools, Langflow Trace (כולל Tool Input/Output), הרצה ב-Playground, והרצה מוצלחת דרך HTTP POST.
