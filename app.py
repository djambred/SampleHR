# app.py
import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import hashlib
import os
from datetime import datetime, timedelta
import json

# Konfigurasi halaman
st.set_page_config(
    page_title="Sistem HR Management",
    page_icon="🏢",
    layout="wide"
)

# Inisialisasi session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'db_initialized' not in st.session_state:
    st.session_state.db_initialized = False

# Database setup
def init_database():
    """Initialize SQLite database with all tables"""
    conn = sqlite3.connect('hr_system.db')
    c = conn.cursor()
    
    # Table users (with roles)
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL,
            employee_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Table departments
    c.execute('''
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kode_department TEXT UNIQUE NOT NULL,
            nama_department TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table employees
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_lengkap TEXT NOT NULL,
            nik TEXT UNIQUE NOT NULL,
            tempat_lahir TEXT,
            tanggal_lahir DATE,
            jenis_kelamin TEXT,
            alamat TEXT,
            telepon TEXT,
            email TEXT UNIQUE,
            status_pernikahan TEXT,
            agama TEXT,
            jabatan TEXT,
            department_id INTEGER,
            status_kerja TEXT,
            foto_path TEXT,
            tanggal_masuk DATE,
            user_id INTEGER,
            FOREIGN KEY (department_id) REFERENCES departments(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Table educations
    c.execute('''
        CREATE TABLE IF NOT EXISTS educations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            jenjang TEXT NOT NULL,
            nama_institusi TEXT NOT NULL,
            jurusan TEXT,
            tahun_masuk INTEGER,
            tahun_lulus INTEGER,
            file_ijazah_path TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
    ''')
    
    # Table certifications
    c.execute('''
        CREATE TABLE IF NOT EXISTS certifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            nama_sertifikat TEXT NOT NULL,
            penerbit TEXT,
            tahun INTEGER,
            file_sertifikat_path TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
    ''')
    
    # Table contracts
    c.execute('''
        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            tanggal_mulai DATE NOT NULL,
            tanggal_berakhir DATE NOT NULL,
            jenis_kontrak TEXT NOT NULL,
            status_kontrak TEXT,
            keterangan TEXT,
            file_kontrak_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
    ''')
    
    # Table leave_submissions
    c.execute('''
        CREATE TABLE IF NOT EXISTS leave_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            tanggal_mulai DATE NOT NULL,
            tanggal_selesai DATE NOT NULL,
            jenis_cuti TEXT NOT NULL,
            alasan TEXT,
            file_pendukung_path TEXT,
            status TEXT DEFAULT 'pending',
            approved_by INTEGER,
            approved_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees(id),
            FOREIGN KEY (approved_by) REFERENCES employees(id)
        )
    ''')
    
    # Table daily_attendances
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_attendances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            tanggal DATE NOT NULL,
            jam_masuk TIME,
            jam_pulang TIME,
            status TEXT,
            keterangan TEXT,
            leave_submission_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees(id),
            FOREIGN KEY (leave_submission_id) REFERENCES leave_submissions(id)
        )
    ''')
    
    conn.commit()
    return conn

def hash_password(password):
    """Hash password menggunakan SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_dummy_data(conn):
    """Create dummy data for the system"""
    c = conn.cursor()
    
    # Check if data already exists
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] > 0:
        return
    
    # Create departments
    departments = [
        ('DEPT001', 'HR Department'),
        ('DEPT002', 'IT Department'),
        ('DEPT003', 'Finance Department'),
        ('DEPT004', 'Marketing Department'),
        ('DEPT005', 'Operations Department')
    ]
    
    c.executemany("INSERT INTO departments (kode_department, nama_department) VALUES (?, ?)", departments)
    
    # Create admin user
    admin_password = hash_password("admin123")
    c.execute("INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)",
              ("admin", admin_password, "admin@hrsystem.com", "admin"))
    
    # Create manager users
    managers = [
        ("manager_hr", "manager123", "hr_manager@hrsystem.com", "manager", 1),
        ("manager_it", "manager123", "it_manager@hrsystem.com", "manager", 2),
        ("manager_fin", "manager123", "fin_manager@hrsystem.com", "manager", 3)
    ]
    
    for manager in managers:
        hashed_pwd = hash_password(manager[1])
        c.execute("INSERT INTO users (username, password, email, role, employee_id) VALUES (?, ?, ?, ?, ?)",
                  (manager[0], hashed_pwd, manager[2], manager[3], manager[4]))
    
    # Create employee users and employees
    employee_data = []
    for i in range(1, 21):
        nama = f"Employee {i}"
        nik = f"NIK{i:03d}"
        dept_id = (i % 5) + 1  # Distribute across 5 departments
        
        # Insert employee
        c.execute('''
            INSERT INTO employees (
                nama_lengkap, nik, tempat_lahir, tanggal_lahir, jenis_kelamin,
                alamat, telepon, email, status_pernikahan, agama, jabatan,
                department_id, status_kerja, tanggal_masuk
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            nama, nik, "Jakarta", "1990-01-01", "Laki-laki" if i % 2 == 0 else "Perempuan",
            f"Jl. Example No.{i}", f"0812345678{i:02d}", f"employee{i}@company.com",
            "Menikah" if i % 3 == 0 else "Belum Menikah", "Islam",
            f"Staff {['IT', 'Finance', 'Marketing', 'HR', 'Operations'][dept_id-1]}",
            dept_id, "aktif", "2023-01-01"
        ))
        
        employee_id = c.lastrowid
        
        # Create user for employee
        username = f"emp{i:03d}"
        password = hash_password("employee123")
        c.execute("INSERT INTO users (username, password, email, role, employee_id) VALUES (?, ?, ?, ?, ?)",
                  (username, password, f"emp{i}@company.com", "employee", employee_id))
        
        # Add education data
        if i % 2 == 0:
            c.execute('''
                INSERT INTO educations (employee_id, jenjang, nama_institusi, jurusan, tahun_masuk, tahun_lulus)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (employee_id, "S1", "Universitas Indonesia", "Teknik Informatika", 2010, 2014))
        
        # Add contract data
        start_date = datetime(2023, 1, 1) + timedelta(days=i*30)
        end_date = start_date + timedelta(days=365)
        c.execute('''
            INSERT INTO contracts (employee_id, tanggal_mulai, tanggal_berakhir, jenis_kontrak, status_kontrak)
            VALUES (?, ?, ?, ?, ?)
        ''', (employee_id, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), "PKWT", "aktif"))
    
    # Add some leave submissions
    for i in range(1, 6):
        start_date = datetime.now() + timedelta(days=i)
        end_date = start_date + timedelta(days=2)
        c.execute('''
            INSERT INTO leave_submissions (employee_id, tanggal_mulai, tanggal_selesai, jenis_cuti, alasan, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (i, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), 
              "Cuti Tahunan", f"Liburan keluarga {i}", "pending"))
    
    # Add attendance data for last 7 days
    for emp_id in range(1, 6):
        for day in range(7):
            date = datetime.now() - timedelta(days=day)
            if date.weekday() < 5:  # Weekdays only
                c.execute('''
                    INSERT INTO daily_attendances (employee_id, tanggal, jam_masuk, jam_pulang, status)
                    VALUES (?, ?, ?, ?, ?)
                ''', (emp_id, date.strftime("%Y-%m-%d"), "08:00:00", "17:00:00", "hadir"))
    
    conn.commit()

def login_user(username, password):
    """Authenticate user"""
    conn = sqlite3.connect('hr_system.db')
    c = conn.cursor()
    
    hashed_password = hash_password(password)
    
    c.execute("SELECT * FROM users WHERE username = ? AND password = ? AND is_active = 1", 
              (username, hashed_password))
    user = c.fetchone()
    
    if user:
        st.session_state.logged_in = True
        st.session_state.user_role = user[4]  # role column
        st.session_state.current_user = user
        return True
    return False

def admin_dashboard():
    """Admin dashboard"""
    st.title("🏢 Admin Dashboard")
    
    conn = sqlite3.connect('hr_system.db')
    
    # Statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_emps = pd.read_sql("SELECT COUNT(*) as count FROM employees", conn)['count'][0]
        st.metric("Total Karyawan", total_emps)
    
    with col2:
        total_depts = pd.read_sql("SELECT COUNT(*) as count FROM departments", conn)['count'][0]
        st.metric("Total Department", total_depts)
    
    with col3:
        pending_leaves = pd.read_sql("SELECT COUNT(*) as count FROM leave_submissions WHERE status = 'pending'", conn)['count'][0]
        st.metric("Cuti Pending", pending_leaves)
    
    with col4:
        active_contracts = pd.read_sql("SELECT COUNT(*) as count FROM contracts WHERE status_kontrak = 'aktif'", conn)['count'][0]
        st.metric("Kontrak Aktif", active_contracts)
    
    # Tabs for different sections
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📋 Karyawan", "🏢 Department", "📝 Kontrak", "🏖️ Cuti", 
        "📊 Attendance", "👥 User Management"
    ])
    
    with tab1:
        st.subheader("Data Karyawan")
        employees = pd.read_sql("""
            SELECT e.*, d.nama_department 
            FROM employees e 
            LEFT JOIN departments d ON e.department_id = d.id
        """, conn)
        st.dataframe(employees, use_container_width=True)
        
        # Add new employee
        with st.expander("➕ Tambah Karyawan Baru"):
            with st.form("add_employee_form"):
                col1, col2 = st.columns(2)
                with col1:
                    nama = st.text_input("Nama Lengkap")
                    nik = st.text_input("NIK")
                    tempat_lahir = st.text_input("Tempat Lahir")
                    tanggal_lahir = st.date_input("Tanggal Lahir")
                    jenis_kelamin = st.selectbox("Jenis Kelamin", ["Laki-laki", "Perempuan"])
                
                with col2:
                    departments = pd.read_sql("SELECT id, nama_department FROM departments", conn)
                    dept_options = {row['nama_department']: row['id'] for _, row in departments.iterrows()}
                    selected_dept = st.selectbox("Department", list(dept_options.keys()))
                    dept_id = dept_options[selected_dept]
                    
                    jabatan = st.text_input("Jabatan")
                    status_kerja = st.selectbox("Status Kerja", ["aktif", "tidak aktif", "resign"])
                
                if st.form_submit_button("Simpan"):
                    c = conn.cursor()
                    c.execute('''
                        INSERT INTO employees (
                            nama_lengkap, nik, tempat_lahir, tanggal_lahir, jenis_kelamin,
                            department_id, jabatan, status_kerja, tanggal_masuk
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (nama, nik, tempat_lahir, tanggal_lahir.strftime("%Y-%m-%d"), 
                          jenis_kelamin, dept_id, jabatan, status_kerja, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    st.success("Karyawan berhasil ditambahkan!")
                    st.rerun()
    
    with tab2:
        st.subheader("Data Department")
        departments = pd.read_sql("SELECT * FROM departments", conn)
        st.dataframe(departments, use_container_width=True)
        
        with st.expander("➕ Tambah Department"):
            with st.form("add_department_form"):
                kode = st.text_input("Kode Department")
                nama = st.text_input("Nama Department")
                
                if st.form_submit_button("Simpan"):
                    c = conn.cursor()
                    c.execute("INSERT INTO departments (kode_department, nama_department) VALUES (?, ?)", 
                              (kode, nama))
                    conn.commit()
                    st.success("Department berhasil ditambahkan!")
                    st.rerun()
    
    with tab3:
        st.subheader("Data Kontrak")
        contracts = pd.read_sql("""
            SELECT c.*, e.nama_lengkap 
            FROM contracts c 
            JOIN employees e ON c.employee_id = e.id
        """, conn)
        st.dataframe(contracts, use_container_width=True)
    
    with tab4:
        st.subheader("Pengajuan Cuti")
        leaves = pd.read_sql("""
            SELECT l.*, e.nama_lengkap 
            FROM leave_submissions l 
            JOIN employees e ON l.employee_id = e.id
            ORDER BY l.created_at DESC
        """, conn)
        st.dataframe(leaves, use_container_width=True)
        
        # Approve/reject leave
        st.subheader("Approval Cuti")
        pending_leaves = pd.read_sql("""
            SELECT l.*, e.nama_lengkap 
            FROM leave_submissions l 
            JOIN employees e ON l.employee_id = e.id
            WHERE l.status = 'pending'
        """, conn)
        
        if not pending_leaves.empty:
            for _, leave in pending_leaves.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"**{leave['nama_lengkap']}** - {leave['jenis_cuti']}")
                        st.write(f"{leave['tanggal_mulai']} s/d {leave['tanggal_selesai']}")
                        st.write(f"Alasan: {leave['alasan']}")
                    
                    with col2:
                        if st.button("✓ Approve", key=f"approve_{leave['id']}"):
                            c = conn.cursor()
                            c.execute("UPDATE leave_submissions SET status = 'approved', approved_date = ? WHERE id = ?",
                                      (datetime.now().strftime("%Y-%m-%d"), leave['id']))
                            conn.commit()
                            st.rerun()
                    
                    with col3:
                        if st.button("✗ Reject", key=f"reject_{leave['id']}"):
                            c = conn.cursor()
                            c.execute("UPDATE leave_submissions SET status = 'rejected' WHERE id = ?",
                                      (leave['id'],))
                            conn.commit()
                            st.rerun()
        else:
            st.info("Tidak ada pengajuan cuti pending")
    
    with tab5:
        st.subheader("Attendance Report")
        attendances = pd.read_sql("""
            SELECT a.*, e.nama_lengkap 
            FROM daily_attendances a 
            JOIN employees e ON a.employee_id = e.id
            ORDER BY a.tanggal DESC
            LIMIT 100
        """, conn)
        st.dataframe(attendances, use_container_width=True)
    
    with tab6:
        st.subheader("User Management")
        users = pd.read_sql("SELECT * FROM users", conn)
        st.dataframe(users, use_container_width=True)
        
        with st.expander("➕ Tambah User Baru"):
            with st.form("add_user_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                email = st.text_input("Email")
                role = st.selectbox("Role", ["admin", "manager", "employee"])
                
                if role == "employee":
                    employees = pd.read_sql("SELECT id, nama_lengkap FROM employees", conn)
                    emp_options = {row['nama_lengkap']: row['id'] for _, row in employees.iterrows()}
                    selected_emp = st.selectbox("Karyawan", list(emp_options.keys()))
                    emp_id = emp_options[selected_emp]
                else:
                    emp_id = None
                
                if st.form_submit_button("Simpan"):
                    c = conn.cursor()
                    hashed_pwd = hash_password(password)
                    c.execute("INSERT INTO users (username, password, email, role, employee_id) VALUES (?, ?, ?, ?, ?)",
                              (username, hashed_pwd, email, role, emp_id))
                    conn.commit()
                    st.success("User berhasil ditambahkan!")
                    st.rerun()

def manager_dashboard():
    """Manager dashboard"""
    st.title("👨‍💼 Manager Dashboard")
    
    conn = sqlite3.connect('hr_system.db')
    user = st.session_state.current_user
    
    # Get manager's department
    c = conn.cursor()
    c.execute("SELECT department_id FROM employees WHERE id = ?", (user[5],))
    result = c.fetchone()
    
    if result:
        dept_id = result[0]
        
        # Department statistics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            c.execute("SELECT COUNT(*) FROM employees WHERE department_id = ?", (dept_id,))
            total_emps = c.fetchone()[0]
            st.metric("Karyawan di Department", total_emps)
        
        with col2:
            c.execute("SELECT COUNT(*) FROM leave_submissions l JOIN employees e ON l.employee_id = e.id WHERE e.department_id = ? AND l.status = 'pending'", 
                      (dept_id,))
            pending_leaves = c.fetchone()[0]
            st.metric("Cuti Pending", pending_leaves)
        
        with col3:
            c.execute("SELECT COUNT(*) FROM employees WHERE department_id = ? AND status_kerja = 'aktif'", 
                      (dept_id,))
            active_emps = c.fetchone()[0]
            st.metric("Karyawan Aktif", active_emps)
        
        # Tabs
        tab1, tab2, tab3 = st.tabs(["📋 Karyawan", "🏖️ Cuti", "📊 Attendance"])
        
        with tab1:
            st.subheader("Karyawan di Department")
            employees = pd.read_sql("""
                SELECT * FROM employees WHERE department_id = ?
            """, conn, params=(dept_id,))
            st.dataframe(employees, use_container_width=True)
        
        with tab2:
            st.subheader("Pengajuan Cuti Department")
            leaves = pd.read_sql("""
                SELECT l.*, e.nama_lengkap 
                FROM leave_submissions l 
                JOIN employees e ON l.employee_id = e.id
                WHERE e.department_id = ?
                ORDER BY l.created_at DESC
            """, conn, params=(dept_id,))
            st.dataframe(leaves, use_container_width=True)
            
            # Approve/reject leave for department
            st.subheader("Approval Cuti Department")
            pending_leaves = pd.read_sql("""
                SELECT l.*, e.nama_lengkap 
                FROM leave_submissions l 
                JOIN employees e ON l.employee_id = e.id
                WHERE e.department_id = ? AND l.status = 'pending'
            """, conn, params=(dept_id,))
            
            if not pending_leaves.empty:
                for _, leave in pending_leaves.iterrows():
                    with st.container():
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.write(f"**{leave['nama_lengkap']}** - {leave['jenis_cuti']}")
                            st.write(f"{leave['tanggal_mulai']} s/d {leave['tanggal_selesai']}")
                            st.write(f"Alasan: {leave['alasan']}")
                        
                        with col2:
                            if st.button("✓ Approve", key=f"m_approve_{leave['id']}"):
                                c = conn.cursor()
                                c.execute("UPDATE leave_submissions SET status = 'approved', approved_by = ?, approved_date = ? WHERE id = ?",
                                          (user[5], datetime.now().strftime("%Y-%m-%d"), leave['id']))
                                conn.commit()
                                st.rerun()
                        
                        with col3:
                            if st.button("✗ Reject", key=f"m_reject_{leave['id']}"):
                                c = conn.cursor()
                                c.execute("UPDATE leave_submissions SET status = 'rejected', approved_by = ?, approved_date = ? WHERE id = ?",
                                          (user[5], datetime.now().strftime("%Y-%m-%d"), leave['id']))
                                conn.commit()
                                st.rerun()
            else:
                st.info("Tidak ada pengajuan cuti pending di department Anda")
        
        with tab3:
            st.subheader("Attendance Department")
            attendances = pd.read_sql("""
                SELECT a.*, e.nama_lengkap 
                FROM daily_attendances a 
                JOIN employees e ON a.employee_id = e.id
                WHERE e.department_id = ?
                ORDER BY a.tanggal DESC
                LIMIT 50
            """, conn, params=(dept_id,))
            st.dataframe(attendances, use_container_width=True)

def employee_dashboard():
    """Employee dashboard"""
    st.title("👤 Employee Dashboard")
    
    conn = sqlite3.connect('hr_system.db')
    user = st.session_state.current_user
    emp_id = user[5]  # employee_id
    
    # Personal information
    col1, col2, col3 = st.columns(3)
    
    with col1:
        c = conn.cursor()
        c.execute("SELECT * FROM employees WHERE id = ?", (emp_id,))
        emp_info = c.fetchone()
        
        if emp_info:
            st.metric("Nama", emp_info[1])
            st.metric("NIK", emp_info[2])
            st.metric("Jabatan", emp_info[11])
    
    with col2:
        # Get department name
        c.execute("""
            SELECT d.nama_department 
            FROM employees e 
            JOIN departments d ON e.department_id = d.id 
            WHERE e.id = ?
        """, (emp_id,))
        dept_name = c.fetchone()[0]
        st.metric("Department", dept_name)
        
        c.execute("SELECT COUNT(*) FROM leave_submissions WHERE employee_id = ? AND status = 'approved'", (emp_id,))
        approved_leaves = c.fetchone()[0]
        st.metric("Cuti Disetujui", approved_leaves)
    
    with col3:
        c.execute("SELECT COUNT(*) FROM contracts WHERE employee_id = ? AND status_kontrak = 'aktif'", (emp_id,))
        active_contracts = c.fetchone()[0]
        st.metric("Kontrak Aktif", active_contracts)
        
        c.execute("SELECT COUNT(*) FROM daily_attendances WHERE employee_id = ? AND status = 'hadir'", (emp_id,))
        attendance_days = c.fetchone()[0]
        st.metric("Hari Hadir", attendance_days)
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Profil", "📝 Kontrak", "🏖️ Cuti", "📊 Attendance"])
    
    with tab1:
        st.subheader("Profil Saya")
        employee = pd.read_sql("SELECT * FROM employees WHERE id = ?", conn, params=(emp_id,))
        st.dataframe(employee, use_container_width=True)
        
        # Education
        st.subheader("Riwayat Pendidikan")
        educations = pd.read_sql("SELECT * FROM educations WHERE employee_id = ?", conn, params=(emp_id,))
        st.dataframe(educations, use_container_width=True)
        
        # Certifications
        st.subheader("Sertifikat")
        certifications = pd.read_sql("SELECT * FROM certifications WHERE employee_id = ?", conn, params=(emp_id,))
        st.dataframe(certifications, use_container_width=True)
    
    with tab2:
        st.subheader("Kontrak Saya")
        contracts = pd.read_sql("SELECT * FROM contracts WHERE employee_id = ?", conn, params=(emp_id,))
        st.dataframe(contracts, use_container_width=True)
    
    with tab3:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Riwayat Cuti")
            leaves = pd.read_sql("SELECT * FROM leave_submissions WHERE employee_id = ?", conn, params=(emp_id,))
            st.dataframe(leaves, use_container_width=True)
        
        with col2:
            st.subheader("Ajukan Cuti")
            with st.form("leave_request_form"):
                jenis_cuti = st.selectbox("Jenis Cuti", ["Cuti Tahunan", "Cuti Sakit", "Cuti Melahirkan", "Cuti Lainnya"])
                tanggal_mulai = st.date_input("Tanggal Mulai")
                tanggal_selesai = st.date_input("Tanggal Selesai")
                alasan = st.text_area("Alasan")
                file_pendukung = st.file_uploader("File Pendukung (opsional)")
                
                if st.form_submit_button("Ajukan Cuti"):
                    c = conn.cursor()
                    c.execute('''
                        INSERT INTO leave_submissions (employee_id, tanggal_mulai, tanggal_selesai, jenis_cuti, alasan, status)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (emp_id, tanggal_mulai.strftime("%Y-%m-%d"), tanggal_selesai.strftime("%Y-%m-%d"), 
                          jenis_cuti, alasan, "pending"))
                    conn.commit()
                    st.success("Pengajuan cuti berhasil dikirim!")
                    st.rerun()
    
    with tab4:
        st.subheader("Riwayat Kehadiran")
        attendances = pd.read_sql("SELECT * FROM daily_attendances WHERE employee_id = ? ORDER BY tanggal DESC LIMIT 30", 
                                  conn, params=(emp_id,))
        st.dataframe(attendances, use_container_width=True)
        
        # Attendance chart
        st.subheader("Chart Kehadiran Bulan Ini")
        current_month = datetime.now().strftime("%Y-%m")
        monthly_attendance = pd.read_sql("""
            SELECT tanggal, status, COUNT(*) as count 
            FROM daily_attendances 
            WHERE employee_id = ? AND strftime('%Y-%m', tanggal) = ?
            GROUP BY tanggal, status
        """, conn, params=(emp_id, current_month))
        
        if not monthly_attendance.empty:
            st.bar_chart(monthly_attendance.pivot_table(index='tanggal', columns='status', values='count', fill_value=0))

def login_page():
    """Login page"""
    st.title("🔐 Login - Sistem HR Management")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submit = st.form_submit_button("Login")
        
        if submit:
            if login_user(username, password):
                st.success("Login berhasil!")
                st.rerun()
            else:
                st.error("Username atau password salah!")

def main():
    """Main application"""
    # Initialize database
    if not st.session_state.db_initialized:
        conn = init_database()
        create_dummy_data(conn)
        st.session_state.db_initialized = True
    
    # Check login status
    if not st.session_state.logged_in:
        login_page()
    else:
        # Sidebar with user info and logout
        with st.sidebar:
            st.write(f"**User:** {st.session_state.current_user[1]}")
            st.write(f"**Role:** {st.session_state.user_role}")
            st.write(f"**Email:** {st.session_state.current_user[3]}")
            
            if st.button("🚪 Logout"):
                st.session_state.logged_in = False
                st.session_state.user_role = None
                st.session_state.current_user = None
                st.rerun()
            
            st.divider()
            
            # Quick stats
            if st.session_state.user_role == "admin":
                conn = sqlite3.connect('hr_system.db')
                today = datetime.now().strftime("%Y-%m-%d")
                leaves_today = pd.read_sql("""
                    SELECT COUNT(*) as count FROM leave_submissions 
                    WHERE DATE(created_at) = ?
                """, conn, params=(today,))['count'][0]
                st.metric("Pengajuan Hari Ini", leaves_today)
        
        # Show appropriate dashboard based on role
        if st.session_state.user_role == "admin":
            admin_dashboard()
        elif st.session_state.user_role == "manager":
            manager_dashboard()
        elif st.session_state.user_role == "employee":
            employee_dashboard()
        else:
            st.error("Role tidak dikenali!")

if __name__ == "__main__":
    main()
