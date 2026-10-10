import sqlite3
import time
from datetime import datetime
import gradio as gr

DB_NAME = "fitness_tracker_oop.db"

# =========================================================
# 1. Database Manager Class
# =========================================================
class DatabaseManager:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Users Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    pin TEXT NOT NULL,
                    age INTEGER NOT NULL,
                    height REAL NOT NULL,
                    weight REAL NOT NULL,
                    goal TEXT NOT NULL,
                    bmi REAL NOT NULL,
                    ideal_weight REAL NOT NULL,
                    target_calories REAL NOT NULL,
                    target_protein REAL NOT NULL
                )
            """)

            # Nutrition Logs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nutrition_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    food_name TEXT NOT NULL,
                    grams REAL NOT NULL,
                    calories REAL NOT NULL,
                    protein REAL NOT NULL,
                    date_str TEXT NOT NULL
                )
            """)

            # Workout Logs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workout_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    exercise_name TEXT NOT NULL,
                    weight REAL NOT NULL,
                    reps INTEGER NOT NULL,
                    sets INTEGER NOT NULL,
                    total_volume REAL NOT NULL,
                    date_str TEXT NOT NULL
                )
            """)

            # Water Logs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS water_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    liters REAL NOT NULL,
                    date_str TEXT NOT NULL
                )
            """)

            # Body Measurements Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS body_measurements (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    weight REAL NOT NULL,
                    chest REAL NOT NULL,
                    arms REAL NOT NULL,
                    waist REAL NOT NULL,
                    thighs REAL NOT NULL,
                    forearms REAL,
                    date_str TEXT NOT NULL
                )
            """)

            # Custom Foods Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS custom_foods (
                    food_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    food_name TEXT NOT NULL,
                    calories_per_100g REAL NOT NULL,
                    protein_per_100g REAL NOT NULL
                )
            """)

            # Custom Exercises Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS custom_exercises (
                    exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    exercise_name TEXT NOT NULL
                )
            """)

            conn.commit()

    def execute_query(self, query, params=()):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid

    def fetch_one(self, query, params=()):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()

    def fetch_all(self, query, params=()):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()


# =========================================================
# 2. User Entity Class
# =========================================================
class User:
    def __init__(self, name, pin, age, height, weight, goal, user_id=None):
        self.user_id = user_id
        self.name = str(name).strip()
        self.pin = str(pin).strip()
        self.age = int(age)
        self.height = float(height)
        self.weight = float(weight)
        self.goal = goal

    def calculate_bmi(self):
        height_m = self.height / 100.0
        bmi = round(self.weight / (height_m ** 2), 1)
        if bmi < 18.5:
            status = "Underweight"
        elif 18.5 <= bmi < 24.9:
            status = "Normal Weight"
        elif 25 <= bmi < 29.9:
            status = "Overweight"
        else:
            status = "Obese"
        return bmi, status

    def calculate_ideal_weight(self):
        if self.height > 152.4:
            return round(48 + 1.1 * (self.height - 152.4), 1)
        return round(self.weight, 1)

    def calculate_targets(self):
        if self.goal == "Bulking":
            calories = round(self.weight * 35)
            protein = round(self.weight * 2.2, 1)
        else:
            calories = round(self.weight * 26)
            protein = round(self.weight * 2.5, 1)
        return calories, protein

    def get_water_target(self):
        target = round((self.weight * 35) / 1000.0, 2)
        max_safe = round(target * 1.8, 2)
        return target, max_safe


# =========================================================
# 3. Main Tracker Service Class (Business Logic)
# =========================================================
class FitnessTracker:
    PREDEFINED_FOODS = {
        "Cooked Chicken Breast": {"calories": 165, "protein": 31.0},
        "Cooked Chicken Thigh": {"calories": 209, "protein": 26.0},
        "Cooked Ground Beef 90/10": {"calories": 215, "protein": 26.0},
        "Grilled Beef Steak": {"calories": 250, "protein": 28.0},
        "Grilled Beef Kofta": {"calories": 280, "protein": 22.0},
        "Cooked Salmon": {"calories": 206, "protein": 22.0},
        "Grilled Tilapia": {"calories": 128, "protein": 26.0},
        "Cooked Shrimp": {"calories": 99, "protein": 24.0},
        "Canned Tuna in Water": {"calories": 116, "protein": 25.5},
        "Boiled Egg": {"calories": 155, "protein": 13.0},
        "Omelette Egg": {"calories": 170, "protein": 12.0},
        "Boiled Egg Whites": {"calories": 52, "protein": 11.0},
        "Cottage Cheese": {"calories": 81, "protein": 11.0},
        "Whey Protein Powder": {"calories": 380, "protein": 80.0},
        "Cooked White Rice": {"calories": 130, "protein": 2.7},
        "Cooked Basmati Rice": {"calories": 121, "protein": 3.0},
        "Cooked Brown Rice": {"calories": 112, "protein": 2.6},
        "Cooked Pasta": {"calories": 131, "protein": 5.0},
        "Boiled Potatoes": {"calories": 87, "protein": 2.0},
        "Baked Potatoes": {"calories": 93, "protein": 2.3},
        "Baked Sweet Potato": {"calories": 90, "protein": 2.0},
        "Cooked Oatmeal with Water": {"calories": 71, "protein": 2.5},
        "Whole Wheat Bread": {"calories": 247, "protein": 9.0},
        "Brown Toast": {"calories": 250, "protein": 10.0},
        "Cooked Lentils": {"calories": 116, "protein": 9.0},
        "Cooked Fava Beans": {"calories": 110, "protein": 7.5},
        "Cooked Chickpeas": {"calories": 164, "protein": 8.9},
        "Peanut Butter": {"calories": 588, "protein": 25.0},
        "Roasted Almonds": {"calories": 579, "protein": 21.0},
        "Walnuts": {"calories": 654, "protein": 15.0},
        "Olive Oil": {"calories": 884, "protein": 0.0},
        "Avocado": {"calories": 160, "protein": 2.0},
        "Banana": {"calories": 89, "protein": 1.1},
        "Apple": {"calories": 52, "protein": 0.3},
        "Orange": {"calories": 47, "protein": 0.9},
        "Strawberries": {"calories": 32, "protein": 0.7}
    }

    PREDEFINED_EXERCISES = [
        "Chest [Machine]: Seated Chest Press Machine",
        "Chest [Machine]: Pec Deck / Butterfly Machine",
        "Chest [Machine]: Cable Crossover Flyes",
        "Chest [Machine]: Smith Machine Bench Press",
        "Chest [Machine]: Smith Machine Incline Press",
        "Chest [Free]: Flat Barbell Bench Press",
        "Chest [Free]: Incline Barbell Bench Press",
        "Chest [Free]: Flat Dumbbell Press",
        "Chest [Free]: Incline Dumbbell Press",
        "Chest [Free]: Dumbbell Flyes",
        "Chest [Body]: Dips for Chest",
        "Chest [Body]: Push-ups",
        "Back [Machine]: Lat Pulldown Wide Grip",
        "Back [Machine]: Lat Pulldown Close Grip",
        "Back [Machine]: Seated Cable Row",
        "Back [Machine]: Assisted Pull-up Machine",
        "Back [Machine]: Lever T-Bar Row Machine",
        "Back [Machine]: Hyperextension Bench",
        "Back [Free]: Barbell Deadlift",
        "Back [Free]: Bent-over Barbell Row",
        "Back [Free]: One-Arm Dumbbell Row",
        "Back [Body]: Pull-ups / Chin-ups",
        "Shoulders [Machine]: Shoulder Press Machine",
        "Shoulders [Machine]: Reverse Pec Deck",
        "Shoulders [Machine]: Cable Lateral Raise",
        "Shoulders [Machine]: Cable Face Pulls",
        "Shoulders [Machine]: Smith Machine Overhead Press",
        "Shoulders [Free]: Overhead Barbell Press",
        "Shoulders [Free]: Seated Dumbbell Shoulder Press",
        "Shoulders [Free]: Dumbbell Lateral Raise",
        "Shoulders [Free]: Dumbbell Front Raise",
        "Shoulders [Free]: Dumbbell Shrugs",
        "Legs [Machine]: Leg Press Machine",
        "Legs [Machine]: Leg Extension Machine",
        "Legs [Machine]: Lying Leg Curl Machine",
        "Legs [Machine]: Seated Leg Curl Machine",
        "Legs [Machine]: Standing Calf Raise Machine",
        "Legs [Machine]: Seated Calf Raise Machine",
        "Legs [Machine]: Abductor / Adductor Machine",
        "Legs [Machine]: Smith Machine Squat",
        "Legs [Free]: Barbell Back Squat",
        "Legs [Free]: Romanian Deadlift",
        "Legs [Free]: Dumbbell Lunges",
        "Legs [Free]: Bulgarian Split Squat",
        "Arms [Machine]: Cable Biceps Curl",
        "Arms [Machine]: Preacher Curl Machine",
        "Arms [Machine]: Cable Triceps Pushdown",
        "Arms [Machine]: Cable Overhead Triceps Extension",
        "Arms [Free]: Barbell Biceps Curl",
        "Arms [Free]: Dumbbell Hammer Curl",
        "Arms [Free]: Dumbbell Incline Curl",
        "Arms [Free]: Skull Crushers",
        "Core [Machine]: Cable Abdominal Crunch",
        "Core [Body]: Hanging Leg Raise",
        "Core [Body]: Plank Hold"
    ]

    def __init__(self):
        self.db = DatabaseManager()

    def login_user(self, user_id, pin):
        try:
            if not user_id or not pin:
                return False, "❌ Please enter both User ID and PIN Code."
            user_id = int(user_id)
            row = self.db.fetch_one("SELECT user_id, name, pin FROM users WHERE user_id = ?", (user_id,))
            if not row:
                return False, f"❌ User ID `{user_id}` not found."
            if str(row[2]).strip() != str(pin).strip():
                return False, "❌ Incorrect PIN Code."
            return True, f"Welcome back, **{row[1]}**!"
        except Exception as e:
            return False, f"❌ Login Error: {str(e)}"

    def register_user(self, name, pin, age, height, weight, goal):
        try:
            if not name or not pin or not age or not height or not weight:
                return None, "❌ Please fill in all required fields."
            if not str(pin).isdigit() or len(str(pin)) < 4:
                return None, "❌ PIN Code must contain numeric digits only (at least 4 digits)."
            if float(age) <= 0 or float(age) > 120:
                return None, "❌ Please enter a valid age."
            if float(height) <= 50 or float(height) > 250:
                return None, "❌ Please enter a valid height in cm."
            if float(weight) <= 20 or float(weight) > 300:
                return None, "❌ Please enter a valid weight in kg."

            user = User(name, pin, age, height, weight, goal)
            bmi, bmi_status = user.calculate_bmi()
            ideal_weight = user.calculate_ideal_weight()
            calories, protein = user.calculate_targets()

            user_id = self.db.execute_query("""
                INSERT INTO users (name, pin, age, height, weight, goal, bmi, ideal_weight, target_calories, target_protein)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user.name, user.pin, user.age, user.height, user.weight, user.goal, bmi, ideal_weight, calories, protein))

            msg = (
                f"🎉 **Account Created Successfully!**\n\n"
                f"🆔 **Your User ID is: `{user_id}`**\n\n"
                f"📊 **Health Report:** BMI: {bmi} ({bmi_status}) | Targets: {calories} kcal, {protein}g protein.\n\n"
                f"⏳ Redirecting to Sign In page in 3 seconds..."
            )
            return user_id, msg
        except Exception as e:
            return None, f"❌ Registration Error: {str(e)}"

    def get_all_foods_for_user(self, user_id):
        foods = dict(self.PREDEFINED_FOODS)
        if user_id:
            custom_rows = self.db.fetch_all("SELECT food_name, calories_per_100g, protein_per_100g FROM custom_foods WHERE user_id = ?", (user_id,))
            for name, cals, prot in custom_rows:
                foods[f"[Custom] {name}"] = {"calories": cals, "protein": prot}
        return foods

    def get_all_exercises_for_user(self, user_id):
        exercises = list(self.PREDEFINED_EXERCISES)
        if user_id:
            custom_rows = self.db.fetch_all("SELECT exercise_name FROM custom_exercises WHERE user_id = ?", (user_id,))
            for (name,) in custom_rows:
                exercises.append(f"[Custom] {name}")
        return exercises

    def add_custom_food(self, user_id, name, cals, prot):
        try:
            if not user_id or not name or cals is None or prot is None:
                return "❌ Please enter valid food details."
            if float(cals) < 0 or float(prot) < 0:
                return "❌ Calories and protein must be non-negative."

            self.db.execute_query("""
                INSERT INTO custom_foods (user_id, food_name, calories_per_100g, protein_per_100g)
                VALUES (?, ?, ?, ?)
            """, (user_id, str(name).strip(), float(cals), float(prot)))

            return f"✅ Custom food **'{name}'** added successfully!"
        except Exception as e:
            return f"❌ Error adding food: {str(e)}"

    def add_custom_exercise(self, user_id, name):
        try:
            if not user_id or not name:
                return "❌ Please enter an exercise name."

            self.db.execute_query("""
                INSERT INTO custom_exercises (user_id, exercise_name)
                VALUES (?, ?)
            """, (user_id, str(name).strip()))

            return f"✅ Custom exercise **'{name}'** added successfully!"
        except Exception as e:
            return f"❌ Error adding exercise: {str(e)}"

    def get_dashboard_summary(self, user_id):
        if not user_id:
            return "No User Logged In", 0, 0, 0

        row = self.db.fetch_one("SELECT name, weight, height, goal, bmi, target_calories, target_protein FROM users WHERE user_id = ?", (user_id,))
        if not row:
            return "User Not Found", 0, 0, 0

        name, weight, height, goal, bmi, target_cals, target_prot = row
        today_str = datetime.now().strftime("%Y-%m-%d")

        # Water
        water_row = self.db.fetch_one("SELECT SUM(liters) FROM water_logs WHERE user_id = ? AND date_str = ?", (user_id, today_str))
        water_consumed = water_row[0] or 0.0
        target_water = round((weight * 35) / 1000.0, 2)
        water_ratio = min(1.0, water_consumed / target_water) if target_water > 0 else 0

        # Nutrition
        nut_row = self.db.fetch_one("SELECT SUM(calories), SUM(protein) FROM nutrition_logs WHERE user_id = ? AND date_str = ?", (user_id, today_str))
        cals_consumed = nut_row[0] or 0.0
        prot_consumed = nut_row[1] or 0.0

        cals_ratio = min(1.0, cals_consumed / target_cals) if target_cals > 0 else 0
        prot_ratio = min(1.0, prot_consumed / target_prot) if target_prot > 0 else 0

        info_md = (
            f"👤 **Name:** {name} | 🆔 **ID:** {user_id}\n\n"
            f"⚖️ **Weight:** {weight} kg | 📐 **Height:** {height} cm | 🎯 **Goal:** {goal} | 📊 **BMI:** {bmi}\n\n"
            f"💧 **Water:** {water_consumed:.2f} / {target_water} L\n"
            f"🔥 **Calories:** {cals_consumed:.1f} / {target_cals} kcal\n"
            f"🥩 **Protein:** {prot_consumed:.1f} / {target_prot} g"
        )

        return info_md, water_ratio, cals_ratio, prot_ratio

    def update_user_profile(self, user_id, new_weight, new_goal):
        try:
            if not user_id:
                return "❌ No user logged in."
            if float(new_weight) <= 20 or float(new_weight) > 300:
                return "❌ Invalid weight."

            row = self.db.fetch_one("SELECT name, pin, age, height FROM users WHERE user_id = ?", (user_id,))
            if not row:
                return "❌ User not found."

            user = User(row[0], row[1], row[2], row[3], new_weight, new_goal, user_id)
            bmi, _ = user.calculate_bmi()
            ideal_weight = user.calculate_ideal_weight()
            calories, protein = user.calculate_targets()

            self.db.execute_query("""
                UPDATE users
                SET weight = ?, goal = ?, bmi = ?, ideal_weight = ?, target_calories = ?, target_protein = ?
                WHERE user_id = ?
            """, (new_weight, new_goal, bmi, ideal_weight, calories, protein, user_id))

            return "✅ Profile updated successfully!"
        except Exception as e:
            return f"❌ Update Error: {str(e)}"

    def log_meal(self, user_id, food_item, grams):
        try:
            if not user_id or not food_item:
                return "❌ Please select a meal."

            user_id = int(user_id)
            grams = float(grams or 0)
            if grams <= 0:
                return "❌ Please enter amount in grams."

            user_row = self.db.fetch_one("SELECT name, target_calories, target_protein FROM users WHERE user_id = ?", (user_id,))
            if not user_row:
                return f"❌ No user found with ID ({user_id})."

            user_name, target_cals, target_prot = user_row
            all_foods = self.get_all_foods_for_user(user_id)
            food_data = all_foods.get(food_item, {"calories": 100, "protein": 10})

            factor = grams / 100.0
            cals = round(food_data["calories"] * factor, 1)
            prot = round(food_data["protein"] * factor, 1)
            today_str = datetime.now().strftime("%Y-%m-%d")

            self.db.execute_query("""
                INSERT INTO nutrition_logs (user_id, food_name, grams, calories, protein, date_str)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, food_item, grams, cals, prot, today_str))

            consumed = self.db.fetch_one("""
                SELECT SUM(calories), SUM(protein) FROM nutrition_logs
                WHERE user_id = ? AND date_str = ?
            """, (user_id, today_str))

            cals_consumed = consumed[0] if consumed[0] else 0.0
            prot_consumed = consumed[1] if consumed[1] else 0.0

            rem_cals = max(0, target_cals - cals_consumed)
            rem_prot = max(0, target_prot - prot_consumed)

            return (
                f"✅ Meal logged for **{user_name}**:\n"
                f"🍲 **{food_item}** ({grams}g) 👈 {cals} kcal | {prot}g protein\n\n"
                f"🥩 **Protein Remaining:** **{rem_prot:.1f}g**\n"
                f"🔥 **Calories Remaining:** **{rem_cals:.1f} kcal**"
            )
        except Exception as e:
            return f"❌ Error: {str(e)}"

    def reset_today_meals(self, user_id):
        try:
            if not user_id:
                return "❌ No user logged in."
            today_str = datetime.now().strftime("%Y-%m-%d")
            self.db.execute_query("DELETE FROM nutrition_logs WHERE user_id = ? AND date_str = ?", (user_id, today_str))
            return f"🔄 Reset today's meals successfully!"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    # =========================================================
    # Water Tracker (With Detailed Health Alerts)
    # =========================================================
    def log_water(self, user_id, amount):
        try:
            if not user_id:
                return "❌ Please enter User ID."

            user_id = int(user_id)
            amount = float(amount)
            today_str = datetime.now().strftime("%Y-%m-%d")

            user_row = self.db.fetch_one("SELECT name, pin, age, height, weight, goal FROM users WHERE user_id = ?", (user_id,))
            if not user_row:
                return f"❌ No user found with ID ({user_id})."

            user = User(user_row[0], user_row[1], user_row[2], user_row[3], user_row[4], user_row[5], user_id)
            target_water, max_safe_water = user.get_water_target()

            self.db.execute_query("INSERT INTO water_logs (user_id, liters, date_str) VALUES (?, ?, ?)", (user_id, amount, today_str))

            total_water_row = self.db.fetch_one("SELECT SUM(liters) FROM water_logs WHERE user_id = ? AND date_str = ?", (user_id, today_str))
            total_water = round(total_water_row[0] or 0.0, 2)
            remaining = round(target_water - total_water, 2)

            output = f"💧 **Logged {amount} L for {user.name} (ID: {user_id})**\n\n"
            output += f"📊 **Total water intake today:** `{total_water} L` out of your daily goal `{target_water} L` (calculated for your weight of {user.weight} kg).\n\n"

            if total_water < target_water:
                output += f"⏳ **Remaining:** `{remaining} L` to reach your daily goal. Keep going! 🥤"
            elif target_water <= total_water <= max_safe_water:
                output += f"🎉 **Congratulations! Great job!** You reached your daily water target successfully 👏✨"
                if total_water > target_water:
                    output += f"\n💡 (You drank {round(total_water - target_water, 2)} L above your target, great if you're training hard)."
            else:
                over_amount = round(total_water - target_water, 2)
                output += (
                    f"🎉 **Goal achieved and exceeded!** ({over_amount}+ L over target).\n\n"
                    f"⚠️ **Important Health Notice:**\n"
                    f"Excessive water intake (over {max_safe_water} L) without intense physical exertion may put strain on kidneys and dilute sodium levels (Water Intoxication).\n"
                    f"👉 **Advice:** That's enough for today, resume tomorrow! 🛑"
                )

            return output

        except Exception as e:
            return f"❌ Error: {str(e)}"

    def log_workout(self, user_id, exercise, weight, reps, sets):
        try:
            if not user_id or not exercise:
                return "❌ Please select an exercise."

            user_id = int(user_id)
            weight = float(weight or 0)
            reps = int(reps or 0)
            sets = int(sets or 0)

            user_row = self.db.fetch_one("SELECT name FROM users WHERE user_id = ?", (user_id,))
            if not user_row:
                return f"❌ User not found."

            current_volume = weight * reps * sets
            today_str = datetime.now().strftime("%Y-%m-%d")

            self.db.execute_query("""
                INSERT INTO workout_logs (user_id, exercise_name, weight, reps, sets, total_volume, date_str)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, exercise, weight, reps, sets, current_volume, today_str))

            return f"✅ Exercise **{exercise}** logged successfully! Total Volume: **{current_volume:.1f} kg**"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    def log_body_measurements(self, user_id, weight, chest, arms, waist, thighs, forearms):
        try:
            if not user_id:
                return "❌ No user logged in."

            user_id = int(user_id)
            weight = float(weight or 0)
            today_str = datetime.now().strftime("%Y-%m-%d")

            self.db.execute_query("""
                INSERT INTO body_measurements (user_id, weight, chest, arms, waist, thighs, forearms, date_str)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, weight, chest or 0, arms or 0, waist or 0, thighs or 0, forearms or 0, today_str))

            # Auto update profile weight
            self.db.execute_query("UPDATE users SET weight = ? WHERE user_id = ?", (weight, user_id))

            return f"✅ Body measurements and new weight ({weight} kg) logged successfully!"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    def get_body_measurements_history(self, user_id):
        try:
            if not user_id:
                return "❌ No user logged in.", []
            rows = self.db.fetch_all("""
                SELECT date_str, weight, chest, arms, waist, thighs, forearms
                FROM body_measurements WHERE user_id = ? ORDER BY log_id DESC
            """, (user_id,))
            return f"📐 **Measurements History:**", rows
        except Exception as e:
            return f"❌ Error: {str(e)}", []

    def get_workout_history(self, user_id, filter_exercise):
        try:
            if not user_id:
                return "❌ No user logged in.", []
            user_id = int(user_id)
            if filter_exercise and filter_exercise != "All Exercises":
                rows = self.db.fetch_all("SELECT date_str, exercise_name, weight, reps, sets, total_volume FROM workout_logs WHERE user_id = ? AND exercise_name = ? ORDER BY log_id DESC", (user_id, filter_exercise))
            else:
                rows = self.db.fetch_all("SELECT date_str, exercise_name, weight, reps, sets, total_volume FROM workout_logs WHERE user_id = ? ORDER BY log_id DESC", (user_id,))
            return f"📜 **Workout History:**", rows
        except Exception as e:
            return f"❌ Error: {str(e)}", []

    def get_nutrition_history(self, user_id):
        try:
            if not user_id:
                return "❌ No user logged in.", []
            rows = self.db.fetch_all("SELECT date_str, food_name, grams, calories, protein FROM nutrition_logs WHERE user_id = ? ORDER BY log_id DESC", (user_id,))
            return f"📜 **Nutrition History:**", rows
        except Exception as e:
            return f"❌ Error: {str(e)}", []


# =========================================================
# 4. UI Manager Class (Gradio Dashboard Interface)
# =========================================================
class GymAppUI:
    def __init__(self, tracker: FitnessTracker):
        self.tracker = tracker
        self.custom_css = """
        body, .gradio-container {
            background: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.85)),
                        url('https://images.unsplash.com/photo-1517838277536-f5f99be501cd?q=80&w=1920') no-repeat center center fixed !important;
            background-size: cover !important;
            color: #ffffff !important;
        }
        .gr-button-primary { background-color: #ff4b4b !important; border: none !important; }
        .gr-button-stop { background-color: #d9534f !important; border: none !important; }
        """

    def build_ui(self):
        with gr.Blocks(title="Gym Pro Tracker", css=self.custom_css) as app:
            current_user_id = gr.State(value=None)

            gr.Markdown("# 🏋️‍♂️ Gym Pro Tracker")

            # =========================================================
            # AUTH SECTION
            # =========================================================
            with gr.Column(visible=True) as auth_box:
                auth_tabs = gr.Tabs()
                with auth_tabs:
                    with gr.Tab("Sign In", id="signin_tab"):
                        gr.Markdown("### Sign in with your User ID and PIN")
                        login_id = gr.Number(label="User ID", precision=0)
                        login_pin = gr.Textbox(label="PIN Code", type="password")
                        btn_login = gr.Button("Sign In", variant="primary")
                        out_login = gr.Markdown()

                    with gr.Tab("Register (New User)", id="register_tab"):
                        gr.Markdown("### Register your profile once to get your unique User ID")
                        with gr.Row():
                            u_name = gr.Textbox(label="Full Name", placeholder="e.g. Ahmed Ali")
                            u_pin = gr.Textbox(label="PIN Code (Numbers only)", type="password", value="1234")
                        with gr.Row():
                            u_age = gr.Number(label="Age", value=22, precision=0)
                            u_height = gr.Number(label="Height in cm", value=175)
                            u_weight = gr.Number(label="Weight in kg", value=75)
                        u_goal = gr.Radio(choices=["Bulking", "Cutting"], value="Bulking", label="Goal")

                        btn_user = gr.Button("Register & Create User ID", variant="primary")
                        out_user = gr.Markdown()

            # =========================================================
            # MAIN DASHBOARD SECTION
            # =========================================================
            with gr.Column(visible=False) as main_dashboard:
                with gr.Row():
                    welcome_msg = gr.Markdown()
                    btn_logout = gr.Button("🚪 Log Out", variant="stop", scale=0)

                with gr.Tabs():
                    # Dashboard Overview Tab
                    with gr.Tab("Dashboard Overview"):
                        gr.Markdown("### 📊 Today's Targets & Profile Overview")
                        dash_info = gr.Markdown()
                        with gr.Row():
                            water_bar = gr.Slider(label="Water Target Progress", minimum=0, maximum=1.0, interactive=False)
                            cals_bar = gr.Slider(label="Calorie Target Progress", minimum=0, maximum=1.0, interactive=False)
                            prot_bar = gr.Slider(label="Protein Target Progress", minimum=0, maximum=1.0, interactive=False)

                        btn_refresh_dash = gr.Button("🔄 Refresh Dashboard", variant="primary")

                        gr.Markdown("---")
                        gr.Markdown("### ✏️ Update Weight / Goal")
                        with gr.Row():
                            up_weight = gr.Number(label="New Weight (kg)", value=75)
                            up_goal = gr.Radio(choices=["Bulking", "Cutting"], value="Bulking", label="New Goal")
                        btn_up_prof = gr.Button("Update Profile")
                        out_up_prof = gr.Markdown()
                        btn_up_prof.click(self.tracker.update_user_profile, inputs=[current_user_id, up_weight, up_goal], outputs=out_up_prof)

                    with gr.Tab("Log Nutrition"):
                        gr.Markdown("### Select or Add Custom Meals")
                        n_food = gr.Dropdown(choices=list(self.tracker.PREDEFINED_FOODS.keys()), label="Select Meal")
                        n_grams = gr.Number(label="Amount in Grams", value=100)

                        btn_nut = gr.Button("Log Meal", variant="primary")
                        out_nut = gr.Markdown()
                        btn_nut.click(self.tracker.log_meal, inputs=[current_user_id, n_food, n_grams], outputs=out_nut)

                        gr.Markdown("---")
                        gr.Markdown("### ➕ Add Custom Food")
                        with gr.Row():
                            cf_name = gr.Textbox(label="Food Name")
                            cf_cals = gr.Number(label="Calories per 100g")
                            cf_prot = gr.Number(label="Protein per 100g")
                        btn_add_cf = gr.Button("Add Custom Food")
                        out_add_cf = gr.Markdown()

                        btn_reset = gr.Button("Reset Today's Meals", variant="stop")
                        out_reset = gr.Markdown()
                        btn_reset.click(self.tracker.reset_today_meals, inputs=current_user_id, outputs=out_reset)

                    with gr.Tab("Water Tracker"):
                        gr.Markdown("### Track your daily water intake")
                        with gr.Row():
                            btn_w1 = gr.Button("💧 +0.25 L")
                            btn_w2 = gr.Button("💧 +0.50 L")
                            btn_w3 = gr.Button("💧 +1.00 L")
                        out_water = gr.Markdown()

                        btn_w1.click(lambda uid: self.tracker.log_water(uid, 0.25), inputs=current_user_id, outputs=out_water)
                        btn_w2.click(lambda uid: self.tracker.log_water(uid, 0.50), inputs=current_user_id, outputs=out_water)
                        btn_w3.click(lambda uid: self.tracker.log_water(uid, 1.00), inputs=current_user_id, outputs=out_water)

                    with gr.Tab("Log Workout"):
                        gr.Markdown("### Log Exercises")
                        ex_name = gr.Dropdown(choices=self.tracker.PREDEFINED_EXERCISES, label="Select Exercise")
                        with gr.Row():
                            ex_weight = gr.Number(label="Weight in kg", value=50)
                            ex_reps = gr.Number(label="Reps", value=10, precision=0)
                            ex_sets = gr.Number(label="Sets", value=3, precision=0)

                        btn_work = gr.Button("Log Workout", variant="primary")
                        out_work = gr.Markdown()
                        btn_work.click(self.tracker.log_workout, inputs=[current_user_id, ex_name, ex_weight, ex_reps, ex_sets], outputs=out_work)

                        gr.Markdown("---")
                        gr.Markdown("### ➕ Add Custom Exercise")
                        ce_name = gr.Textbox(label="New Exercise Name")
                        btn_add_ce = gr.Button("Add Custom Exercise")
                        out_add_ce = gr.Markdown()

                    with gr.Tab("Body Measurements"):
                        gr.Markdown("### Body Measurements (cm)")
                        with gr.Row():
                            m_weight = gr.Number(label="Current Weight in kg", value=75)
                            m_chest = gr.Number(label="Chest")
                            m_arms = gr.Number(label="Arms")
                        with gr.Row():
                            m_waist = gr.Number(label="Waist")
                            m_thighs = gr.Number(label="Thighs")
                            m_forearms = gr.Number(label="Forearms")

                        btn_meas = gr.Button("Log Measurements", variant="primary")
                        out_meas = gr.Markdown()
                        btn_meas.click(self.tracker.log_body_measurements, inputs=[current_user_id, m_weight, m_chest, m_arms, m_waist, m_thighs, m_forearms], outputs=out_meas)

                        btn_mhist = gr.Button("Show Measurements History")
                        out_mhist_title = gr.Markdown()
                        out_mhist_table = gr.Dataframe(headers=["Date", "Weight", "Chest", "Arms", "Waist", "Thighs", "Forearms"])
                        btn_mhist.click(self.tracker.get_body_measurements_history, inputs=current_user_id, outputs=[out_mhist_title, out_mhist_table])

                    with gr.Tab("Workout History"):
                        h_filter = gr.Dropdown(choices=["All Exercises"] + self.tracker.PREDEFINED_EXERCISES, value="All Exercises", label="Filter")
                        btn_hist = gr.Button("Show Workout History", variant="primary")
                        out_hist_title = gr.Markdown()
                        out_hist_table = gr.Dataframe(headers=["Date", "Exercise", "Weight", "Reps", "Sets", "Total Volume"])
                        btn_hist.click(self.tracker.get_workout_history, inputs=[current_user_id, h_filter], outputs=[out_hist_title, out_hist_table])

                    with gr.Tab("Nutrition History"):
                        btn_nhist = gr.Button("Show Nutrition History", variant="primary")
                        out_nhist_title = gr.Markdown()
                        out_nhist_table = gr.Dataframe(headers=["Date", "Meal Name", "Grams", "Calories", "Protein"])
                        btn_nhist.click(self.tracker.get_nutrition_history, inputs=current_user_id, outputs=[out_nhist_title, out_nhist_table])

            # =========================================================
            # EVENT HANDLERS
            # =========================================================
            def refresh_ui_dropdowns(uid):
                foods = list(self.tracker.get_all_foods_for_user(uid).keys())
                exes = self.tracker.get_all_exercises_for_user(uid)
                return gr.update(choices=foods, value=foods[0] if foods else None), gr.update(choices=exes, value=exes[0] if exes else None)

            def handle_login(uid, pin):
                success, msg = self.tracker.login_user(uid, pin)
                if success:
                    dash_md, w_r, c_r, p_r = self.tracker.get_dashboard_summary(uid)
                    food_up, ex_up = refresh_ui_dropdowns(uid)
                    return (
                        gr.update(visible=False),
                        gr.update(visible=True),
                        int(uid),
                        f"### {msg}",
                        "",
                        dash_md, w_r, c_r, p_r,
                        food_up, ex_up
                    )
                else:
                    return (
                        gr.update(visible=True),
                        gr.update(visible=False),
                        None,
                        "",
                        msg,
                        "", 0, 0, 0,
                        gr.update(), gr.update()
                    )

            def handle_register(name, pin, age, height, weight, goal):
                user_id, msg = self.tracker.register_user(name, pin, age, height, weight, goal)
                if user_id is not None:
                    gr.Info(f"🎉 Account Created! Your User ID is {user_id}. Redirecting to Sign In...")
                    time.sleep(3)
                    return gr.update(selected="signin_tab"), user_id, msg
                return gr.update(), None, msg

            def handle_add_cf(uid, name, cals, prot):
                res = self.tracker.add_custom_food(uid, name, cals, prot)
                foods = list(self.tracker.get_all_foods_for_user(uid).keys())
                return res, gr.update(choices=foods)

            def handle_add_ce(uid, name):
                res = self.tracker.add_custom_exercise(uid, name)
                exes = self.tracker.get_all_exercises_for_user(uid)
                return res, gr.update(choices=exes)

            def handle_logout():
                return gr.update(visible=True), gr.update(visible=False), None

            btn_login.click(
                handle_login,
                inputs=[login_id, login_pin],
                outputs=[auth_box, main_dashboard, current_user_id, welcome_msg, out_login, dash_info, water_bar, cals_bar, prot_bar, n_food, ex_name]
            )

            btn_user.click(
                handle_register,
                inputs=[u_name, u_pin, u_age, u_height, u_weight, u_goal],
                outputs=[auth_tabs, login_id, out_user]
            )

            btn_refresh_dash.click(
                self.tracker.get_dashboard_summary,
                inputs=current_user_id,
                outputs=[dash_info, water_bar, cals_bar, prot_bar]
            )

            btn_add_cf.click(
                handle_add_cf,
                inputs=[current_user_id, cf_name, cf_cals, cf_prot],
                outputs=[out_add_cf, n_food]
            )

            btn_add_ce.click(
                handle_add_ce,
                inputs=[current_user_id, ce_name],
                outputs=[out_add_ce, ex_name]
            )

            btn_logout.click(
                handle_logout,
                inputs=None,
                outputs=[auth_box, main_dashboard, current_user_id]
            )

        return app

# =========================================================
# Application Entry Point
# =========================================================
if __name__ == "__main__":
    tracker_service = FitnessTracker()
    ui_app = GymAppUI(tracker_service)
    app = ui_app.build_ui()
    app.launch()