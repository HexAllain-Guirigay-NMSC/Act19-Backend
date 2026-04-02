## 🚀 Backend Setup Guide (Flask API)

Follow these steps to run the backend locally:

---

### 📌 1. Clone the Repository

```bash
git clone <https://github.com/HexAllain-Guirigay-NMSC/Act19-Backend>
cd Act19-Backend
```

---

### 📌 2. Create Virtual Environment (venv)

```bash
python -m venv venv
```

---

### 📌 3. Activate Virtual Environment

#### 👉 Windows:

```bash
venv\Scripts\activate
```

#### 👉 Linux / Mac:

```bash
source venv/bin/activate
```

---

### 📌 4. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 📌 5. Setup Database

1. Open **phpMyAdmin** or MySQL
2. Create database:

```sql
CREATE DATABASE gis_db;
```

3. Import the file:

```
gis_db.sql
```

---


### 📌 6. Run the Backend Server

```bash
python app.py
```

---

### 🌐 Server URL

```
http://localhost:5000
```

---

### 🧪 Test Endpoint

```
http://localhost:5000/api/test-db
```

---

### 📂 Important Notes

* Upload folders are already included:

  * `uploads/profile/`
  * `uploads/locations/`
* Placeholders are used to keep folders in GitHub

---


### 👨‍💻 Author

HexAllain Guirigay
