# הרצה מקומית עם Docker

## הרצה
```bash
docker-compose up -d
```

- Langflow: http://localhost:7860
- Postgres: localhost:5432 (משתמש: `langflow`, סיסמה: `langflow`)

## שמירת נתונים
שני ה-volumes (`langflow_data`, `postgres_data`) מחזיקים את הנתונים על הדיסק. עצירה והפעלה מחדש לא מוחקות כלום:
```bash
docker-compose stop
docker-compose start
```
מחיקה מלאה (כולל הנתונים) רק אם תרצו לאפס הכל:
```bash
docker-compose down -v
```

## מסדי הנתונים
ה-container של Postgres מחזיק שני DBs נפרדים:
- `langflow_meta` — משמש את Langflow עצמו לשמירת ה-Flows וההיסטוריה.
- `support_db` — נוצר אוטומטית מ-[db/init/01_create_support_requests.sql](db/init/01_create_support_requests.sql) בהפעלה הראשונה בלבד, ומכיל את טבלת `support_requests` עם הנתונים לדוגמה.

> הסקריפט ב-`db/init` רץ **פעם אחת בלבד**, כשה-volume של Postgres ריק (הפעלה ראשונה). אם תרצו להריץ אותו מחדש, צריך קודם `docker-compose down -v` (מוחק את הנתונים) ואז `docker-compose up -d`.

## חיבור ה-SQL Tool ב-Langflow
בתוך ה-Flow ב-Langflow, מחרוזת החיבור ל-`support_db` (מתוך רשת ה-Docker הפנימית):
```
postgresql://langflow:langflow@postgres:5432/support_db
```

אם תרצו להתחבר מהמחשב שלכם (למשל עם DBeaver/pgAdmin לבדיקה ידנית):
```
postgresql://langflow:langflow@localhost:5432/support_db
```

## Secrets / Global Variables
אין לשים מפתחות API (Gmail, LLM provider וכו') בתוך ה-Flow עצמו. יש להגדיר אותם דרך **Settings → Global Variables** בממשק של Langflow, ולהצביע אליהם מתוך רכיבי ה-Agent/Tool.
