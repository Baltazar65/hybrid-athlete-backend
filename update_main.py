import os

file_path = "main.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Pydantic Modelleri Ekle
models_target = """class SaveModel(BaseModel):
    user_id: str
    weight: float
    goals: str
    frequency: Optional[int] = 3
    focus: Optional[str] = ""
    equipment: Optional[str] = ""
    custom_date: Optional[str] = None"""

models_replacement = models_target + """

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
    date: str"""

content = content.replace(models_target, models_replacement)

# 2. SQLite Tablolarini Ekle
tables_target = """        await db.execute(\"\"\"
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
        \"\"\")
        await db.commit()"""

tables_replacement = """        await db.execute(\"\"\"
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
        \"\"\")

        await db.execute(\"\"\"
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
        \"\"\")

        await db.execute(\"\"\"
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
        \"\"\")

        await db.execute(\"\"\"
            CREATE TABLE IF NOT EXISTS progress_photos (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                photo_data TEXT NOT NULL,
                note TEXT DEFAULT '',
                date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        \"\"\")

        await db.execute(\"\"\"
            CREATE TABLE IF NOT EXISTS water_intake (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                amount_ml REAL NOT NULL,
                date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        \"\"\")

        await db.execute(\"\"\"
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
        \"\"\")

        await db.execute(\"\"\"
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
        \"\"\")

        await db.execute(\"\"\"
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
        \"\"\")
        await db.commit()"""

content = content.replace(tables_target, tables_replacement)

# 3. Yeni API Endpointleri Ekle
endpoints_str = """
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
"""

target_end = """# =========================================================================
# SUNUCU BASLATMA
# =========================================================================
if __name__ == "__main__":"""

content = content.replace(target_end, endpoints_str + "\n" + target_end)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("main.py basariyla guncellendi.")
