# מדד מומנטום בחירות 2026 — הוראות פריסה על Render.com

מדריך מלא לאדם לא טכני. כל שלב מוסבר בפירוט.

---

## שלב 0 — בדיקה ראשונה (על המחשב שלך)

לפני שמעלים לענן — בדוק שהכל עובד אצלך:

```bash
pip install requests feedparser cloudscraper pytrends
python test_sources.py
```

ראה אילו מקורות מסומנים ✅ ואילו ❌. **גם אם חלק נכשלים — הווידג'ט עובד עם מה שיש.**

---

## שלב 1 — יצירת חשבון GitHub (אם אין לך)

1. גש לאתר **github.com**
2. לחץ **Sign Up** ↗
3. צור חשבון עם כתובת מייל
4. אשר את המייל

---

## שלב 2 — העלאת הקבצים ל-GitHub

### אם אתה משתמש בפרויקט הנוכחי:
הקבצים כבר מועלים ל-GitHub — המשך לשלב 3.

### אם אתה מתחיל מחדש:
1. גש ל-**github.com/new** וצור Repository חדש
   - שם: `election-momentum-2026`
   - בחר **Public**
   - לחץ **Create repository**
2. גרור את הקבצים האלה לתוך הדף:
   - `app.py`
   - `collector.py`
   - `widget.html`
   - `requirements.txt`
   - `render.yaml`
3. לחץ **Commit changes**

---

## שלב 3 — יצירת חשבון Render.com

1. גש לאתר **render.com**
2. לחץ **Get Started for Free**
3. לחץ **Continue with GitHub** — כך Render תתחבר לחשבון GitHub שלך
4. אשר את ההרשאות

---

## שלב 4 — פריסת הפרויקט על Render

1. בתוך Render, לחץ **New +** בפינה השמאלית-עליונה
2. בחר **Web Service**
3. לחץ **Connect** ליד ה-Repository `election-momentum-2026`
4. מלא את השדות:
   - **Name**: `election-momentum-2026` (או כל שם אחר)
   - **Region**: Frankfurt (הכי קרוב לישראל)
   - **Branch**: `main`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120`
   - **Instance Type**: **Free**
5. לחץ **Create Web Service**

**המתן 3–5 דקות** — Render מתקין את החבילות ומפעיל את השרת.

---

## שלב 5 — קבלת ה-URL שלך

אחרי שהפריסה מסתיימת, Render יראה לך URL שנראה כך:
```
https://election-momentum-2026.onrender.com
```

בדוק שהכל עובד — פתח ב-Browser:
```
https://election-momentum-2026.onrender.com/data.json
```

אם אתה רואה JSON עם מפלגות — הכל עובד! 🎉

---

## שלב 6 — עדכון ה-URL בווידג'ט

פתח את הקובץ `widget.html` בעורך טקסט פשוט (Notepad / TextEdit).
מצא את השורה:
```javascript
var API_URL = "https://YOUR-APP-NAME.onrender.com/data.json";
```
החלף `YOUR-APP-NAME` בשם האמיתי שלך, למשל:
```javascript
var API_URL = "https://election-momentum-2026.onrender.com/data.json";
```
שמור את הקובץ ועדכן ב-GitHub (גרור ושחרר).

---

## שלב 7 — הטמעה ב-WordPress

1. פתח את `widget.html` בעורך טקסט — **סמן הכל** (Ctrl+A / Cmd+A) — **העתק** (Ctrl+C)
2. היכנס ל-WordPress שלך → ערוך את העמוד/פוסט שבו תרצה את הווידג'ט
3. לחץ **+** להוספת בלוק חדש → חפש **Custom HTML**
4. **הדבק** (Ctrl+V) את כל הקוד
5. לחץ **פרסם** / **עדכן**

זהו! הווידג'ט מופיע בעמוד ומתעדכן כל 30 דקות אוטומטית.

---

## טיפים חשובים

### Render — Free Tier מתנדנד:
השרת "נרדם" אחרי 15 דקות ללא פניות. **בפנייה הראשונה** (כניסה ראשונה לעמוד) יש המתנה של כ-30–60 שניות — **זה נורמלי**. לאחר מכן — מהיר.
- **פתרון פשוט**: שירות חינמי כמו [UptimeRobot.com](https://uptimerobot.com) מבצע ping לשרת כל 5 דקות ומונע את ה-sleep.

### אם מקורות נכשלים:
הווידג'ט מציג אוטומטית "חלק מהנתונים לא זמינים כרגע" וממשיך לעבוד עם שאר המקורות.

### אם רוצים לעדכן בתדירות גבוהה יותר:
שנה ב-`app.py` את הערך `hours=6` ל-`hours=3` למשל.

---

## מבנה הקבצים

```
election-momentum-2026/
├── app.py           ← שרת Flask (לא לגעת)
├── collector.py     ← לוגיקת איסוף נתונים
├── widget.html      ← הווידג'ט (כאן מחליפים API_URL)
├── requirements.txt ← חבילות Python
├── render.yaml      ← הגדרות Render
└── test_sources.py  ← בדיקה מקומית לפני פריסה
```

---

## עזרה נוספת

בעיה? כתוב לצוות הדיגיטל עם:
1. צילום מסך של השגיאה
2. ה-URL של הפרויקט ב-Render
3. תיאור מה עשית

בהצלחה! 🗳️
