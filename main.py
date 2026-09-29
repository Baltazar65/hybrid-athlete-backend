from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager
import bcrypt
import jwt
import os
import uuid
import datetime
import aiosqlite
import traceback
from dotenv import load_dotenv

load_dotenv()

# =========================================================================
# VERITABANI AYARLARI (SQLite)
# =========================================================================
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hybrid_athlete.db")
JWT_SECRET = os.getenv("JWT_SECRET", "hybrid_athlete_super_secret_key_2026")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# =========================================================================
# GEMINI AI KOC ENTEGRASYONU
# =========================================================================
gemini_client = None
try:
    if GEMINI_API_KEY and GEMINI_API_KEY != "BURAYA_GEMINI_API_KEY_YAZ":
        from google import genai
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        print("[OK] Gemini AI Koc aktif.")
    else:
        print("[INFO] Gemini API key bulunamadi. AI Koc devre disi.")
except Exception as e:
    print(f"[WARN] Gemini yuklenemedi: {e}")


async def generate_ai_advice(weight, goals, frequency, focus, equipment):
    if not gemini_client:
        return generate_offline_advice(weight, goals, frequency, focus, equipment)

    prompt = f"""Sen profesyonel bir hibrit atlet kocusun. Hem dovus sporlari hem de guc antrenmani konusunda uzmansin.
Asagidaki sporcu bilgilerine gore kisisellestirilmis bir antrenman programi ve strateji hazirla.

SPORCU BILGILERI:
- Mevcut Kilo: {weight} kg
- Hedefler: {goals}
- Haftalik Antrenman Sikligi: {frequency} gun
- Ana Brans / Odak Alani: {focus}
- Mevcut Ekipmanlar: {equipment}

CEVAP FORMATI (3 bolum, ## ile ayir):
1. Ilk bolum: Genel strateji ve analiz (3-4 cumle)
2. Ikinci bolum (## ile ayir): Haftalik antrenman programi (gun gun detayli)
3. Ucuncu bolum (## ile ayir): Motivasyon ve zihinsel kocluk notu (2-3 cumle, motive edici)

Turkce cevap ver. Kisa ve oz ol ama detayli program ver."""

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return response.text
    except Exception as e:
        print(f"[ERROR] Gemini API Hatasi: {e}")
        return generate_offline_advice(weight, goals, frequency, focus, equipment)


def generate_offline_advice(weight, goals, frequency, focus, equipment):
    """Gemini API olmadan kisisellestirilmis antrenman programi ureten template sistemi."""
    freq = int(frequency) if frequency else 3
    w = float(weight) if weight else 75
    focus_lower = (focus or "").lower()
    goals_lower = (goals or "").lower()
    equip_lower = (equipment or "").lower()

    # Odak alanina gore strateji belirle
    if any(k in focus_lower for k in ["dovus", "mma", "boks", "muay", "kickboks", "gures"]):
        strategy_type = "dovus"
    elif any(k in focus_lower for k in ["guc", "kas", "bench", "squat", "deadlift", "powerlifting"]):
        strategy_type = "guc"
    elif any(k in focus_lower for k in ["kosu", "kardio", "dayaniklilik", "maraton"]):
        strategy_type = "kardio"
    else:
        strategy_type = "hibrit"

    # Kilo bazli analiz
    if w < 65:
        weight_note = f"{w} kg ile hafif siklet kategorisinde yer aliyorsun. Hiz ve ceviklik avantajini kullan."
    elif w < 80:
        weight_note = f"{w} kg ile orta siklet kategorisinde yer aliyorsun. Guc-hiz dengesi cok onemli."
    elif w < 95:
        weight_note = f"{w} kg ile agir orta siklet kategorisinde yer aliyorsun. Guc potansiyelin yuksek."
    else:
        weight_note = f"{w} kg ile agir siklet kategorisinde yer aliyorsun. Patlayici guc ve dayaniklilik onceligin olmali."

    # Strateji bolumu
    strategy = f"{weight_note} "
    if strategy_type == "dovus":
        strategy += f"Hedefiniz '{goals}' dogrultusunda dovus sporlarina odakli bir program hazirlandi. Haftalik {freq} gun antrenman ile teknik calisma, kondisyon ve guc dengesini kuruyoruz. Ekipman durumunuz ({equipment or 'belirtilmemis'}) goz onune alinarak program adapte edildi."
    elif strategy_type == "guc":
        strategy += f"Hedefiniz '{goals}' dogrultusunda guc artisina odakli bir program hazirlandi. Haftalik {freq} gun antrenman ile progresif yuklenme prensibi uygulanacak. {equipment or 'Mevcut ekipmanlar'} kullanilarak maksimal guc gelistirme hedefleniyor."
    elif strategy_type == "kardio":
        strategy += f"Hedefiniz '{goals}' dogrultusunda dayaniklilik odakli bir program hazirlandi. Haftalik {freq} gun ile aerobik ve anaerobik kapasite arttirilacak."
    else:
        strategy += f"Hedefiniz '{goals}' dogrultusunda hem guc hem kondisyon gelistiren hibrit bir program hazirlandi. Haftalik {freq} gun ile cok yonlu atletik gelisim hedefleniyor. {equipment or 'Mevcut ekipmanlar'} kullanilarak program olusturuldu."

    # Haftalik program bolumu
    days = ["Pazartesi", "Sali", "Carsamba", "Persembe", "Cuma", "Cumartesi", "Pazar"]
    program_lines = []

    if strategy_type == "dovus":
        templates = [
            "Teknik calisma (30dk) + Kol ve omuz gucu (3x10 bicep curl, 3x10 overhead press) + 15dk ip atlama",
            "Sparring/Pad calismasi (45dk) + Core guclendirme (3x15 plank, 3x20 russian twist)",
            "Bacak gucu (4x8 squat, 3x12 lunges) + 20dk intervalli kosu (30sn sprint / 30sn yuruyus)",
            "Teknik drilleri (40dk) + Cekme hareketleri (3x10 barfiks, 3x12 bent-over row)",
            "Full body kondisyon (circuit: 10 burpee, 15 kettlebell swing, 20 box jump x 4 tur) + Esneklik",
            "Hafif kardiyo (30dk yuruyus veya hafif kosu) + Mobilite ve esneme",
            "DINLENME - Aktif toparlanma, kopuk banyosu veya hafif yuruyus"
        ]
    elif strategy_type == "guc":
        templates = [
            "Gögüs + Triceps: Bench Press 4x6, Incline DB Press 3x8, Dips 3xMax, Triceps Pushdown 3x12",
            "Sırt + Biceps: Deadlift 4x5, Barbell Row 3x8, Lat Pulldown 3x10, Barbell Curl 3x10",
            "DINLENME veya hafif kardiyo (20dk yuruyus)",
            "Bacak: Squat 4x6, Leg Press 3x10, Romanian DL 3x8, Leg Curl 3x12, Calf Raise 4x15",
            "Omuz + Core: OHP 4x6, Lateral Raise 3x15, Face Pull 3x15, Plank 3x45sn, Hanging Leg Raise 3x12",
            "Full Body Guc: Power Clean 3x5, Front Squat 3x6, Push Press 3x8, Pull-ups 3xMax",
            "DINLENME - Hafif esneme ve mobilite calismasi"
        ]
    elif strategy_type == "kardio":
        templates = [
            "Uzun mesafe kosu (40-60dk zone 2) + Core calismasi (3x20 plank, 3x15 bicycle crunch)",
            "Interval antrenmani: 8x400m (90sn dinlenme) + 10dk soguma",
            "Cross training: 30dk bisiklet + 15dk kurek + Core circuit",
            "Tempo kosu: 30dk orta-yuksek tempo + Bacak guclendirme (3x15 squat, 3x12 lunges)",
            "Bayir kosulari: 10x100m bayir sprint + 20dk duz kosu + Esneme",
            "Uzun yavas kosu (60-80dk) + Mobilite ve foam rolling",
            "DINLENME - Aktif toparlanma, hafif yuruyus veya yuzme"
        ]
    else:
        templates = [
            "Ust govde gucu: Bench Press 4x8, Barbell Row 3x8, OHP 3x10 + 15dk HIIT finisher",
            "Kondisyon: 30dk intervalli kosu + Core circuit (plank, russian twist, leg raise x 3 tur)",
            "Bacak gucu: Squat 4x8, Romanian DL 3x10, Lunges 3x12 + 10dk ip atlama",
            "Teknik/Beceri: Dovus sporlari drilleri veya spesifik spor calismasi (40dk) + Esneme",
            "Full Body: Power Clean 3x5, Front Squat 3x8, Pull-ups 3xMax, Push-ups 3x20 + 15dk kosu",
            "Aktif dinlenme: 30dk yuruyus veya hafif bisiklet + Mobilite + Foam rolling",
            "DINLENME - Tam dinlenme gunu. Bol uyku ve beslenmeye odaklan."
        ]

    for i in range(min(freq + 1, 7)):
        day = days[i % 7]
        workout = templates[i % len(templates)]
        has_equip = equip_lower and equip_lower not in ["yok", "hicbir sey", ""]
        if not has_equip and any(k in workout.lower() for k in ["bench", "barbell", "lat pulldown", "leg press", "cable"]):
            workout = workout.replace("Bench Press", "Push-up (goblet press veya floor press)")
            workout = workout.replace("Barbell Row", "DB Row veya inverted row")
        program_lines.append(f"{day}: {workout}")

    if freq < 6:
        remaining = [d for d in days if d not in [days[i % 7] for i in range(min(freq + 1, 7))]]
        for d in remaining:
            program_lines.append(f"{d}: DINLENME")

    program = "\n".join(program_lines)

    # Motivasyon bolumu
    motivations = [
        f"Unutma, {freq} gun duzenli antrenman bile buyuk fark yaratir. Her tekrar seni daha guclu yapiyor. Hedefin '{goals}' - buna layiksin ve basaracaksin!",
        f"Basari tesadufi degildir. Her gun biraz daha iyi ol. {w} kg'lik bedenini bir savaş makinesine dönüştürecek disiplini göster. Sen bir hibrit atletsin!",
        f"Dünden daha güçlüsün. Bugün antrenmanını yap, yarın sonuçlarını gör. Hedefin '{goals}' - bu yolda tek rakibin dünkü kendinsin!",
    ]
    import random
    motivation = random.choice(motivations)

    return f"{strategy} ## {program} ## {motivation}"


# =========================================================================
# VERITABANI BASLATMA
# =========================================================================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                weight REAL NOT NULL,
                goals TEXT NOT NULL,
                frequency INTEGER DEFAULT 3,
                focus TEXT DEFAULT '',
                equipment TEXT DEFAULT '',
                advice TEXT DEFAULT '',
                custom_date TEXT,
                created_at TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS nutrition (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                meal_name TEXT NOT NULL,
                food_name TEXT NOT NULL,
                calories REAL DEFAULT 0,
                protein REAL DEFAULT 0,
                carbs REAL DEFAULT 0,
                fat REAL DEFAULT 0,
                date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS measurements (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                chest REAL,
                waist REAL,
                arm REAL,
                leg REAL,
                hip REAL,
                neck REAL,
                date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS progress_photos (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                photo_data TEXT NOT NULL,
                note TEXT DEFAULT '',
                date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS water_intake (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                amount_ml REAL NOT NULL,
                date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS sleep_log (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                sleep_time TEXT NOT NULL,
                wake_time TEXT NOT NULL,
                quality INTEGER DEFAULT 3,
                note TEXT DEFAULT '',
                date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS one_rm (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                exercise TEXT NOT NULL,
                weight REAL NOT NULL,
                reps INTEGER NOT NULL,
                estimated_1rm REAL NOT NULL,
                date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS training_log (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                mood INTEGER DEFAULT 3,
                energy INTEGER DEFAULT 3,
                date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        await db.commit()
    print(f"[OK] SQLite veritabani hazir: {DB_PATH}")


@asynccontextmanager
async def lifespan(app):
    await init_db()
    yield


# =========================================================================
# UYGULAMA AYARLARI
# =========================================================================
app = FastAPI(title="Hybrid Athlete API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================================
# PYDANTIC MODELLER
# =========================================================================
class RegisterModel(BaseModel):
    first_name: str
    last_name: str
    username: str
    password: str
    email: str


class LoginModel(BaseModel):
    username: str
    password: str


class SaveModel(BaseModel):
    user_id: str
    weight: float
    goals: str
    frequency: Optional[int] = 3
    focus: Optional[str] = ""
    equipment: Optional[str] = ""
    custom_date: Optional[str] = None

class NutritionModel(BaseModel):
    user_id: str
    meal_name: str
    food_name: str
    calories: float = 0
    protein: float = 0
    carbs: float = 0
    fat: float = 0
    date: str

class MeasurementModel(BaseModel):
    user_id: str
    chest: Optional[float] = None
    waist: Optional[float] = None
    arm: Optional[float] = None
    leg: Optional[float] = None
    hip: Optional[float] = None
    neck: Optional[float] = None
    date: str

class PhotoModel(BaseModel):
    user_id: str
    photo_data: str
    note: Optional[str] = ""
    date: str

class WaterModel(BaseModel):
    user_id: str
    amount_ml: float
    date: str

class SleepModel(BaseModel):
    user_id: str
    sleep_time: str
    wake_time: str
    quality: Optional[int] = 3
    note: Optional[str] = ""
    date: str

class OneRMModel(BaseModel):
    user_id: str
    exercise: str
    weight: float
    reps: int
    estimated_1rm: float
    date: str

class TrainingLogModel(BaseModel):
    user_id: str
    title: str
    content: str
    mood: Optional[int] = 3
    energy: Optional[int] = 3
    date: str

class NutritionModel(BaseModel):
    user_id: str
    meal_name: str
    food_name: str
    calories: float = 0
    protein: float = 0
    carbs: float = 0
    fat: float = 0
    date: str

class MeasurementModel(BaseModel):
    user_id: str
    chest: Optional[float] = None
    waist: Optional[float] = None
    arm: Optional[float] = None
    leg: Optional[float] = None
    hip: Optional[float] = None
    neck: Optional[float] = None
    date: str

class PhotoModel(BaseModel):
    user_id: str
    photo_data: str
    note: Optional[str] = ""
    date: str

class WaterModel(BaseModel):
    user_id: str
    amount_ml: float
    date: str

class SleepModel(BaseModel):
    user_id: str
    sleep_time: str
    wake_time: str
    quality: Optional[int] = 3
    note: Optional[str] = ""
    date: str

class OneRMModel(BaseModel):
    user_id: str
    exercise: str
    weight: float
    reps: int
    estimated_1rm: float
    date: str

class TrainingLogModel(BaseModel):
    user_id: str
    title: str
    content: str
    mood: Optional[int] = 3
    energy: Optional[int] = 3
    date: str


# =========================================================================
# YARDIMCI FONKSIYONLAR
# =========================================================================
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


# =========================================================================
# API ENDPOINTLERI
# =========================================================================

@app.get("/")
async def root():
    return {"status": "success", "message": "Hybrid Athlete API v2.0 calisiyor! (SQLite)"}


@app.post("/api/register")
async def register(data: RegisterModel):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT id FROM users WHERE username = ?", (data.username.strip().lower(),))
            if await cursor.fetchone():
                raise HTTPException(status_code=400, detail="Bu kullanici adi zaten alinmis!")

            cursor = await db.execute("SELECT id FROM users WHERE email = ?", (data.email.strip().lower(),))
            if await cursor.fetchone():
                raise HTTPException(status_code=400, detail="Bu e-posta adresi zaten kayitli!")

            hashed = hash_password(data.password)
            user_id = str(uuid.uuid4())
            await db.execute(
                "INSERT INTO users (id, first_name, last_name, username, password, email, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, data.first_name.strip(), data.last_name.strip(), data.username.strip().lower(),
                 hashed, data.email.strip().lower(), datetime.datetime.utcnow().isoformat())
            )
            await db.commit()

        return {"status": "success", "message": "Kayit basarili!"}
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Sunucu hatasi: {str(e)}")


@app.post("/api/login")
async def login(data: LoginModel):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE username = ?", (data.username.strip().lower(),))
            user = await cursor.fetchone()

        if not user:
            raise HTTPException(status_code=401, detail="Kullanici bulunamadi!")

        if not verify_password(data.password, user["password"]):
            raise HTTPException(status_code=401, detail="Sifre yanlis!")

        token = jwt.encode(
            {
                "username": user["username"],
                "exp": datetime.datetime.utcnow() + datetime.timedelta(days=30),
            },
            JWT_SECRET,
            algorithm="HS256",
        )

        return {
            "status": "success",
            "token": token,
            "username": user["username"],
            "first_name": user["first_name"],
        }
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Sunucu hatasi: {str(e)}")


@app.post("/api/save")
async def save_period(data: SaveModel):
    try:
        advice = await generate_ai_advice(
            data.weight, data.goals, data.frequency, data.focus, data.equipment
        )

        record_id = str(uuid.uuid4())
        created_at = datetime.datetime.utcnow().isoformat()

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO history (id, user_id, weight, goals, frequency, focus, equipment, advice, custom_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (record_id, data.user_id, data.weight, data.goals, data.frequency,
                 data.focus, data.equipment, advice, data.custom_date, created_at)
            )
            await db.commit()

        return {
            "status": "success",
            "advice": advice,
            "data": {
                "_id": record_id,
                "user_id": data.user_id,
                "weight": data.weight,
                "goals": data.goals,
                "frequency": data.frequency,
                "focus": data.focus,
                "equipment": data.equipment,
                "advice": advice,
                "custom_date": data.custom_date,
                "created_at": created_at,
            },
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Sunucu hatasi: {str(e)}")


@app.get("/api/history")
async def get_history(user_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM history WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
            )
            rows = await cursor.fetchall()

        items = []
        for row in rows:
            items.append({
                "_id": row["id"],
                "user_id": row["user_id"],
                "weight": row["weight"],
                "goals": row["goals"],
                "frequency": row["frequency"],
                "focus": row["focus"],
                "equipment": row["equipment"],
                "advice": row["advice"],
                "custom_date": row["custom_date"],
                "created_at": row["created_at"],
            })

        return {"status": "success", "data": items}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Sunucu hatasi: {str(e)}")


@app.delete("/api/delete/{record_id}")
async def delete_record(record_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("DELETE FROM history WHERE id = ?", (record_id,))
            await db.commit()
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Kayit bulunamadi!")

        return {"status": "success", "message": "Kayit silindi!"}
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Sunucu hatasi: {str(e)}")



# =========================================================================
# YENI OZELLIK API ENDPOINTLERI
# =========================================================================

# --- BESLENME TAKIBI ---
@app.post("/api/nutrition")
async def add_nutrition(data: NutritionModel):
    try:
        record_id = str(uuid.uuid4())
        created_at = datetime.datetime.utcnow().isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO nutrition (id, user_id, meal_name, food_name, calories, protein, carbs, fat, date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (record_id, data.user_id, data.meal_name, data.food_name, data.calories, data.protein, data.carbs, data.fat, data.date, created_at)
            )
            await db.commit()
        return {"status": "success", "message": "Beslenme kaydi eklendi."}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/nutrition")
async def get_nutrition(user_id: str, date: str = None):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            if date:
                cursor = await db.execute("SELECT * FROM nutrition WHERE user_id = ? AND date = ? ORDER BY created_at DESC", (user_id, date))
            else:
                cursor = await db.execute("SELECT * FROM nutrition WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
            rows = await cursor.fetchall()
        items = [{**dict(row), "_id": row["id"]} for row in rows]
        return {"status": "success", "data": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/nutrition/{record_id}")
async def delete_nutrition(record_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM nutrition WHERE id = ?", (record_id,))
            await db.commit()
        return {"status": "success", "message": "Silindi"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- VUCUT OLCULERI ---
@app.post("/api/measurements")
async def add_measurement(data: MeasurementModel):
    try:
        record_id = str(uuid.uuid4())
        created_at = datetime.datetime.utcnow().isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO measurements (id, user_id, chest, waist, arm, leg, hip, neck, date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (record_id, data.user_id, data.chest, data.waist, data.arm, data.leg, data.hip, data.neck, data.date, created_at)
            )
            await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/measurements")
async def get_measurements(user_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM measurements WHERE user_id = ? ORDER BY date DESC, created_at DESC", (user_id,))
            rows = await cursor.fetchall()
        items = [{**dict(row), "_id": row["id"]} for row in rows]
        return {"status": "success", "data": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/measurements/{record_id}")
async def delete_measurement(record_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM measurements WHERE id = ?", (record_id,))
            await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- ILERLEME FOTOGRAFLARI ---
@app.post("/api/photos")
async def add_photo(data: PhotoModel):
    try:
        record_id = str(uuid.uuid4())
        created_at = datetime.datetime.utcnow().isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO progress_photos (id, user_id, photo_data, note, date, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (record_id, data.user_id, data.photo_data, data.note, data.date, created_at)
            )
            await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/photos")
async def get_photos(user_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM progress_photos WHERE user_id = ? ORDER BY date DESC, created_at DESC", (user_id,))
            rows = await cursor.fetchall()
        items = [{**dict(row), "_id": row["id"]} for row in rows]
        return {"status": "success", "data": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/photos/{record_id}")
async def delete_photo(record_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM progress_photos WHERE id = ?", (record_id,))
            await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- SU TUKETIMI ---
@app.post("/api/water")
async def add_water(data: WaterModel):
    try:
        record_id = str(uuid.uuid4())
        created_at = datetime.datetime.utcnow().isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO water_intake (id, user_id, amount_ml, date, created_at) VALUES (?, ?, ?, ?, ?)",
                (record_id, data.user_id, data.amount_ml, data.date, created_at)
            )
            await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/water")
async def get_water(user_id: str, date: str = None):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            if date:
                cursor = await db.execute("SELECT * FROM water_intake WHERE user_id = ? AND date = ? ORDER BY created_at DESC", (user_id, date))
            else:
                cursor = await db.execute("SELECT * FROM water_intake WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
            rows = await cursor.fetchall()
        items = [{**dict(row), "_id": row["id"]} for row in rows]
        return {"status": "success", "data": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/water/{record_id}")
async def delete_water(record_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM water_intake WHERE id = ?", (record_id,))
            await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- UYKU TAKIBI ---
@app.post("/api/sleep")
async def add_sleep(data: SleepModel):
    try:
        record_id = str(uuid.uuid4())
        created_at = datetime.datetime.utcnow().isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO sleep_log (id, user_id, sleep_time, wake_time, quality, note, date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (record_id, data.user_id, data.sleep_time, data.wake_time, data.quality, data.note, data.date, created_at)
            )
            await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sleep")
async def get_sleep(user_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM sleep_log WHERE user_id = ? ORDER BY date DESC, created_at DESC", (user_id,))
            rows = await cursor.fetchall()
        items = [{**dict(row), "_id": row["id"]} for row in rows]
        return {"status": "success", "data": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sleep/{record_id}")
async def delete_sleep(record_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM sleep_log WHERE id = ?", (record_id,))
            await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 1RM HESAPLAYICI ---
@app.post("/api/onerm")
async def add_onerm(data: OneRMModel):
    try:
        record_id = str(uuid.uuid4())
        created_at = datetime.datetime.utcnow().isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO one_rm (id, user_id, exercise, weight, reps, estimated_1rm, date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (record_id, data.user_id, data.exercise, data.weight, data.reps, data.estimated_1rm, data.date, created_at)
            )
            await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/onerm")
async def get_onerm(user_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM one_rm WHERE user_id = ? ORDER BY date DESC, created_at DESC", (user_id,))
            rows = await cursor.fetchall()
        items = [{**dict(row), "_id": row["id"]} for row in rows]
        return {"status": "success", "data": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/onerm/{record_id}")
async def delete_onerm(record_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM one_rm WHERE id = ?", (record_id,))
            await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- ANTRENMAN GUNLUGU ---
@app.post("/api/training-log")
async def add_training_log(data: TrainingLogModel):
    try:
        record_id = str(uuid.uuid4())
        created_at = datetime.datetime.utcnow().isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO training_log (id, user_id, title, content, mood, energy, date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (record_id, data.user_id, data.title, data.content, data.mood, data.energy, data.date, created_at)
            )
            await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/training-log")
async def get_training_log(user_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM training_log WHERE user_id = ? ORDER BY date DESC, created_at DESC", (user_id,))
            rows = await cursor.fetchall()
        items = [{**dict(row), "_id": row["id"]} for row in rows]
        return {"status": "success", "data": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/training-log/{record_id}")
async def delete_training_log(record_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM training_log WHERE id = ?", (record_id,))
            await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================================================================
# DASHBOARD OZET ENDPOINT
# =========================================================================
@app.get("/api/dashboard")
async def get_dashboard(user_id: str):
    """Gunluk ozet dashboard verisi dondurur."""
    try:
        today = datetime.date.today().isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row

            # Gunluk kalori/makro toplami
            cursor = await db.execute(
                "SELECT COALESCE(SUM(calories),0) as total_cal, COALESCE(SUM(protein),0) as total_pro, COALESCE(SUM(carbs),0) as total_carb, COALESCE(SUM(fat),0) as total_fat FROM nutrition WHERE user_id = ? AND date = ?",
                (user_id, today)
            )
            nutrition_row = await cursor.fetchone()

            # Gunluk su toplami
            cursor = await db.execute(
                "SELECT COALESCE(SUM(amount_ml),0) as total_water FROM water_intake WHERE user_id = ? AND date = ?",
                (user_id, today)
            )
            water_row = await cursor.fetchone()

            # Son uyku kaydi
            cursor = await db.execute(
                "SELECT sleep_time, wake_time, quality FROM sleep_log WHERE user_id = ? ORDER BY date DESC, created_at DESC LIMIT 1",
                (user_id,)
            )
            sleep_row = await cursor.fetchone()

            # Son periyot (AI koc tavsiyesi)
            cursor = await db.execute(
                "SELECT weight, focus, advice, custom_date, created_at FROM history WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
                (user_id,)
            )
            period_row = await cursor.fetchone()

            # Toplam antrenman gunlugu sayisi (streak icin)
            cursor = await db.execute(
                "SELECT COUNT(*) as total_logs FROM training_log WHERE user_id = ?",
                (user_id,)
            )
            log_count_row = await cursor.fetchone()

            # Son 7 gun antrenman sayisi
            cursor = await db.execute(
                "SELECT COUNT(DISTINCT date) as active_days FROM training_log WHERE user_id = ? AND date >= date('now', '-7 days')",
                (user_id,)
            )
            weekly_row = await cursor.fetchone()

        dashboard = {
            "today": today,
            "nutrition": {
                "calories": nutrition_row["total_cal"] if nutrition_row else 0,
                "protein": nutrition_row["total_pro"] if nutrition_row else 0,
                "carbs": nutrition_row["total_carb"] if nutrition_row else 0,
                "fat": nutrition_row["total_fat"] if nutrition_row else 0,
            },
            "water_ml": water_row["total_water"] if water_row else 0,
            "sleep": {
                "sleep_time": sleep_row["sleep_time"] if sleep_row else None,
                "wake_time": sleep_row["wake_time"] if sleep_row else None,
                "quality": sleep_row["quality"] if sleep_row else None,
            },
            "last_period": {
                "weight": period_row["weight"] if period_row else None,
                "focus": period_row["focus"] if period_row else None,
                "advice_preview": (period_row["advice"][:150] + "...") if period_row and period_row["advice"] else None,
                "date": period_row["custom_date"] or period_row["created_at"] if period_row else None,
            },
            "stats": {
                "total_logs": log_count_row["total_logs"] if log_count_row else 0,
                "weekly_active_days": weekly_row["active_days"] if weekly_row else 0,
            }
        }
        return {"status": "success", "data": dashboard}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))



# =========================================================================
# YENI OZELLIK API ENDPOINTLERI
# =========================================================================

# --- BESLENME TAKIBI ---
@app.post("/api/nutrition")
async def add_nutrition(data: NutritionModel):
    try:
        record_id = str(uuid.uuid4())
        created_at = datetime.datetime.utcnow().isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO nutrition (id, user_id, meal_name, food_name, calories, protein, carbs, fat, date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (record_id, data.user_id, data.meal_name, data.food_name, data.calories, data.protein, data.carbs, data.fat, data.date, created_at)
            )
            await db.commit()
        return {"status": "success", "message": "Beslenme kaydi eklendi."}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/nutrition")
async def get_nutrition(user_id: str, date: str = None):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            if date:
                cursor = await db.execute("SELECT * FROM nutrition WHERE user_id = ? AND date = ? ORDER BY created_at DESC", (user_id, date))
            else:
                cursor = await db.execute("SELECT * FROM nutrition WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
            rows = await cursor.fetchall()
        return {"status": "success", "data": [dict(row) for row in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/nutrition/{record_id}")
async def delete_nutrition(record_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM nutrition WHERE id = ?", (record_id,))
            await db.commit()
        return {"status": "success", "message": "Silindi"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- VUCUT OLCULERI ---
@app.post("/api/measurements")
async def add_measurement(data: MeasurementModel):
    try:
        record_id = str(uuid.uuid4())
        created_at = datetime.datetime.utcnow().isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO measurements (id, user_id, chest, waist, arm, leg, hip, neck, date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (record_id, data.user_id, data.chest, data.waist, data.arm, data.leg, data.hip, data.neck, data.date, created_at)
            )
            await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/measurements")
async def get_measurements(user_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM measurements WHERE user_id = ? ORDER BY date DESC, created_at DESC", (user_id,))
            rows = await cursor.fetchall()
        return {"status": "success", "data": [dict(row) for row in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/measurements/{record_id}")
async def delete_measurement(record_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM measurements WHERE id = ?", (record_id,))
            await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- ILERLEME FOTOGRAFLARI ---
@app.post("/api/photos")
async def add_photo(data: PhotoModel):
    try:
        record_id = str(uuid.uuid4())
        created_at = datetime.datetime.utcnow().isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO progress_photos (id, user_id, photo_data, note, date, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (record_id, data.user_id, data.photo_data, data.note, data.date, created_at)
            )
            await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/photos")
async def get_photos(user_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM progress_photos WHERE user_id = ? ORDER BY date DESC, created_at DESC", (user_id,))
            rows = await cursor.fetchall()
        return {"status": "success", "data": [dict(row) for row in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/photos/{record_id}")
async def delete_photo(record_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM progress_photos WHERE id = ?", (record_id,))
            await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- SU TUKETIMI ---
@app.post("/api/water")
async def add_water(data: WaterModel):
    try:
        record_id = str(uuid.uuid4())
        created_at = datetime.datetime.utcnow().isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO water_intake (id, user_id, amount_ml, date, created_at) VALUES (?, ?, ?, ?, ?)",
                (record_id, data.user_id, data.amount_ml, data.date, created_at)
            )
            await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/water")
async def get_water(user_id: str, date: str = None):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            if date:
                cursor = await db.execute("SELECT * FROM water_intake WHERE user_id = ? AND date = ? ORDER BY created_at DESC", (user_id, date))
            else:
                cursor = await db.execute("SELECT * FROM water_intake WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
            rows = await cursor.fetchall()
        return {"status": "success", "data": [dict(row) for row in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/water/{record_id}")
async def delete_water(record_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM water_intake WHERE id = ?", (record_id,))
            await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- UYKU TAKIBI ---
@app.post("/api/sleep")
async def add_sleep(data: SleepModel):
    try:
        record_id = str(uuid.uuid4())
        created_at = datetime.datetime.utcnow().isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO sleep_log (id, user_id, sleep_time, wake_time, quality, note, date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (record_id, data.user_id, data.sleep_time, data.wake_time, data.quality, data.note, data.date, created_at)
            )
            await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sleep")
async def get_sleep(user_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM sleep_log WHERE user_id = ? ORDER BY date DESC, created_at DESC", (user_id,))
            rows = await cursor.fetchall()
        return {"status": "success", "data": [dict(row) for row in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sleep/{record_id}")
async def delete_sleep(record_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM sleep_log WHERE id = ?", (record_id,))
            await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 1RM HESAPLAYICI ---
@app.post("/api/onerm")
async def add_onerm(data: OneRMModel):
    try:
        record_id = str(uuid.uuid4())
        created_at = datetime.datetime.utcnow().isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO one_rm (id, user_id, exercise, weight, reps, estimated_1rm, date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (record_id, data.user_id, data.exercise, data.weight, data.reps, data.estimated_1rm, data.date, created_at)
            )
            await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/onerm")
async def get_onerm(user_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM one_rm WHERE user_id = ? ORDER BY date DESC, created_at DESC", (user_id,))
            rows = await cursor.fetchall()
        return {"status": "success", "data": [dict(row) for row in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/onerm/{record_id}")
async def delete_onerm(record_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM one_rm WHERE id = ?", (record_id,))
            await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- ANTRENMAN GUNLUGU ---
@app.post("/api/training-log")
async def add_training_log(data: TrainingLogModel):
    try:
        record_id = str(uuid.uuid4())
        created_at = datetime.datetime.utcnow().isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO training_log (id, user_id, title, content, mood, energy, date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (record_id, data.user_id, data.title, data.content, data.mood, data.energy, data.date, created_at)
            )
            await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/training-log")
async def get_training_log(user_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM training_log WHERE user_id = ? ORDER BY date DESC, created_at DESC", (user_id,))
            rows = await cursor.fetchall()
        return {"status": "success", "data": [dict(row) for row in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/training-log/{record_id}")
async def delete_training_log(record_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM training_log WHERE id = ?", (record_id,))
            await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- DASHBOARD OZET ---
@app.get("/api/dashboard")
async def get_dashboard(user_id: str):
    try:
        today = datetime.date.today().isoformat()
        week_ago = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row

            # Bugunku beslenme
            cursor = await db.execute(
                "SELECT COALESCE(SUM(calories),0) as calories, COALESCE(SUM(protein),0) as protein, COALESCE(SUM(carbs),0) as carbs, COALESCE(SUM(fat),0) as fat FROM nutrition WHERE user_id = ? AND date = ?",
                (user_id, today)
            )
            nutrition_row = await cursor.fetchone()
            nutrition = dict(nutrition_row) if nutrition_row else {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}

            # Bugunku su
            cursor = await db.execute(
                "SELECT COALESCE(SUM(amount_ml),0) as total FROM water_intake WHERE user_id = ? AND date = ?",
                (user_id, today)
            )
            water_row = await cursor.fetchone()
            water_ml = water_row["total"] if water_row else 0

            # Son uyku
            cursor = await db.execute(
                "SELECT * FROM sleep_log WHERE user_id = ? ORDER BY date DESC, created_at DESC LIMIT 1",
                (user_id,)
            )
            sleep_row = await cursor.fetchone()
            sleep = dict(sleep_row) if sleep_row else None

            # Son periyot (AI koc)
            cursor = await db.execute(
                "SELECT * FROM history WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
                (user_id,)
            )
            last_period_row = await cursor.fetchone()
            last_period = None
            if last_period_row:
                lp = dict(last_period_row)
                last_period = {
                    "weight": lp.get("weight"),
                    "advice_preview": (lp.get("advice") or "")[:200],
                    "date": lp.get("custom_date") or lp.get("created_at", "")[:10],
                }

            # Haftalik istatistikler
            cursor = await db.execute(
                "SELECT COUNT(DISTINCT date) as active_days FROM training_log WHERE user_id = ? AND date >= ?",
                (user_id, week_ago)
            )
            weekly_row = await cursor.fetchone()
            weekly_active = weekly_row["active_days"] if weekly_row else 0

            # Toplam kayit sayisi
            total_logs = 0
            for table in ["nutrition", "water_intake", "sleep_log", "one_rm", "training_log", "measurements"]:
                cursor = await db.execute(f"SELECT COUNT(*) as cnt FROM {table} WHERE user_id = ?", (user_id,))
                cnt_row = await cursor.fetchone()
                total_logs += cnt_row["cnt"] if cnt_row else 0

        return {
            "status": "success",
            "data": {
                "nutrition": nutrition,
                "water_ml": water_ml,
                "sleep": sleep,
                "last_period": last_period,
                "stats": {
                    "weekly_active_days": weekly_active,
                    "total_logs": total_logs,
                }
            }
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# SUNUCU BASLATMA
# =========================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
