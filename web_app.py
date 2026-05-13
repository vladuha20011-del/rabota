# web_app.py - ФИНАЛЬНАЯ ВЕРСИЯ
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import mysql.connector
import hashlib
import pymysql
import json
import secrets
import webbrowser
import threading
import re
import time
from datetime import datetime

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

MYSQL_USER = "support"
MYSQL_PASSWORD = "vdfCD3r34$def"
MYSQL_PORT = 3306

# ---------------------- ЛОКАЛЬНАЯ БД ----------------------
class Database:
    def __init__(self):
        self._init_db()

    def _get_conn(self):
        return mysql.connector.connect(
            host='localhost',
            user='web_user',
            password='Dkflbckfd2000',
            database='web_app_db'
        )

    def execute_query(self, query, params=None, fetch_one=False, fetch_all=False):
        conn = self._get_conn()
        cursor = conn.cursor(dictionary=True)
        try:
            if params is None:
                cursor.execute(query)
            else:
                if isinstance(params, tuple):
                    # Заменяем ? на %s если нужно
                    query = query.replace('?', '%s')
                    cursor.execute(query, params)
                else:
                    cursor.execute(query, (params,))
            
            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                conn.commit()
                return cursor.lastrowid
        finally:
            cursor.close()
            conn.close()

    def _init_db(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(255) NOT NULL,
            role VARCHAR(50) DEFAULT 'user',
            is_active INT DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS servers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            region_code VARCHAR(50) UNIQUE NOT NULL,
            region_name VARCHAR(255) NOT NULL,
            host VARCHAR(255) NOT NULL,
            database_name VARCHAR(255) NOT NULL,
            db_type VARCHAR(50) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS user_server_access (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            server_id INT NOT NULL,
            can_view INT DEFAULT 1,
            can_export INT DEFAULT 0,
            UNIQUE KEY user_server_unique (user_id, server_id)
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS queries (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            sql_text TEXT NOT NULL,
            parameters TEXT,
            server_type VARCHAR(50),
            created_by INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS user_query_access (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            query_id INT NOT NULL,
            can_view INT DEFAULT 1,
            UNIQUE KEY user_query_unique (user_id, query_id)
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            username VARCHAR(100),
            action VARCHAR(255),
            details TEXT,
            ip_address VARCHAR(50),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        admin_pass = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute("INSERT IGNORE INTO users (id, username, password_hash, full_name, role) VALUES (1, 'admin', %s, 'Administrator', 'admin')", (admin_pass,))
        
        conn.commit()
        cursor.close()
        conn.close()

db = Database()

# ---------------------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------------------
def log_action(user_id, username, action, details, ip=""):
    db.execute_query(
        "INSERT INTO logs (user_id, username, action, details, ip_address) VALUES (%s, %s, %s, %s, %s)",
        (user_id, username, action, details, ip)
    )

def get_user_servers(user_id, user_role):
    if user_role == 'admin':
        data = db.execute_query("SELECT id, region_code, region_name, host, database_name, db_type FROM servers", fetch_all=True) or []
    else:
        data = db.execute_query("""
            SELECT s.id, s.region_code, s.region_name, s.host, s.database_name, s.db_type 
            FROM servers s
            JOIN user_server_access usa ON s.id = usa.server_id
            WHERE usa.user_id = %s AND usa.can_view = 1
        """, (user_id,), fetch_all=True) or []
    return [{"id": d["id"], "code": d["region_code"], "name": d["region_name"], "host": d["host"], "database": d["database_name"], "type": d["db_type"]} for d in data]

def get_user_queries(user_id, user_role):
    if user_role == 'admin':
        data = db.execute_query("SELECT id, name, description FROM queries", fetch_all=True) or []
    else:
        data = db.execute_query("""
            SELECT q.id, q.name, q.description 
            FROM queries q
            LEFT JOIN user_query_access uqa ON q.id = uqa.query_id AND uqa.user_id = %s
            WHERE uqa.can_view = 1 OR q.created_by = %s
        """, (user_id, user_id), fetch_all=True) or []
    return [{"id": d["id"], "name": d["name"], "description": d["description"]} for d in data]

def generate_password(length=10):
    alphabet = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def get_db_connection(server_id):
    server = db.execute_query("SELECT host, database_name FROM servers WHERE id = %s", (server_id,), fetch_one=True)
    if not server:
        return None, "Сервер не найден"
    try:
        db_conn = pymysql.connect(
            host=server["host"], user=MYSQL_USER, password=MYSQL_PASSWORD,
            database=server["database_name"], port=MYSQL_PORT, charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor, connect_timeout=10
        )
        return db_conn, None
    except Exception as e:
        return None, str(e)

# ---------------------- HTML ШАБЛОН (УПРОЩЕННЫЙ) ----------------------
MAIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Система запросов к БД</title>
    <meta charset="utf-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; }
        .header { background: #1a1a2e; color: white; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px; }
        .logo { font-size: 22px; font-weight: bold; }
        .user-info { display: flex; gap: 15px; align-items: center; flex-wrap: wrap; }
        .btn-header { background: rgba(255,255,255,0.15); color: white; border: none; padding: 8px 18px; border-radius: 6px; cursor: pointer; text-decoration: none; font-size: 13px; }
        .btn-header:hover { background: rgba(255,255,255,0.25); }
        .container { max-width: 1600px; margin: 20px auto; padding: 0 20px; }
        .tabs { display: flex; gap: 8px; margin-bottom: 25px; flex-wrap: wrap; border-bottom: 2px solid #ddd; padding-bottom: 10px; }
        .tab { padding: 10px 24px; background: white; border: none; border-radius: 8px 8px 0 0; cursor: pointer; font-size: 14px; font-weight: 500; color: #555; }
        .tab:hover { background: #e0e0e0; }
        .tab.active { background: #4a86e8; color: white; }
        .query-desc { background: #e8f4f8; padding: 15px 20px; border-radius: 10px; margin-bottom: 20px; border-left: 4px solid #4a86e8; }
        .params-panel { background: white; padding: 25px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .params-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; margin-bottom: 25px; }
        .param-field { display: flex; flex-direction: column; }
        .param-field label { font-size: 13px; font-weight: 600; margin-bottom: 6px; color: #555; }
        .param-field input, .param-field select { padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
        .region-row { display: flex; gap: 15px; align-items: flex-end; flex-wrap: wrap; margin-top: 10px; padding-top: 15px; border-top: 1px solid #eee; }
        .region-select { flex: 2; min-width: 200px; }
        .search-btn button { background: #4a86e8; color: white; border: none; padding: 10px 30px; border-radius: 6px; cursor: pointer; font-size: 15px; font-weight: bold; }
        .results { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow-x: auto; }
        .results-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap; gap: 10px; }
        .export-btn { background: #28a745; color: white; border: none; padding: 6px 15px; border-radius: 5px; cursor: pointer; font-size: 13px; }
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
        th { background: #4a86e8; color: white; font-weight: 600; }
        tr:hover { background: #f5f5f5; cursor: pointer; }
        .loading { text-align: center; padding: 60px; color: #999; }
        .error { color: #dc3545; padding: 15px; background: #ffe0e0; border-radius: 8px; margin: 10px 0; }
        .info { color: #856404; padding: 15px; background: #fff3cd; border-radius: 8px; margin: 10px 0; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; overflow: auto; }
        .modal-content { background: white; margin: 3% auto; width: 90%; max-width: 900px; border-radius: 12px; max-height: 90%; overflow-y: auto; }
        .modal-header { padding: 20px 25px; background: #1a1a2e; color: white; border-radius: 12px 12px 0 0; display: flex; justify-content: space-between; align-items: center; }
        .modal-header h2 { font-size: 20px; }
        .close { cursor: pointer; font-size: 28px; line-height: 20px; }
        .modal-body { padding: 25px; }
        .card { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
        .btn-icon { background: none; border: none; cursor: pointer; font-size: 18px; padding: 5px 10px; border-radius: 5px; }
        .btn-icon:hover { background: #ddd; }
        .btn-add { background: #28a745; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; margin-top: 10px; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: 500; }
        .form-group input, .form-group select, .form-group textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; }
        .access-checkboxes { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 8px; margin-top: 10px; max-height: 200px; overflow-y: auto; padding: 10px; background: #f8f9fa; border-radius: 8px; }
    </style>
</head>
<body>
    {% if not session.user %}
    <div style="max-width: 420px; margin: 100px auto; background: white; padding: 35px; border-radius: 16px;">
        <h2>🔐 Вход в систему</h2>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="post">
            <div class="form-group"><label>Логин</label><input type="text" name="username" required></div>
            <div class="form-group"><label>Пароль</label><input type="password" name="password" required></div>
            <button type="submit">Войти</button>
        </form>
    </div>
    {% else %}
    <div class="header">
        <div class="logo">📊 Система запросов к БД</div>
        <div class="user-info">
            <span>👋 {{ session.user.full_name }} ({{ session.user.username }})</span>
            {% if session.user.role == 'admin' %}
            <button class="btn-header" onclick="openAdminServers()">🖥 Серверы</button>
            <button class="btn-header" onclick="openAdminQueries()">📋 Запросы</button>
            <button class="btn-header" onclick="openAdminUsers()">👥 Пользователи</button>
            <button class="btn-header" onclick="openAdminLogs()">📜 Логи</button>
            {% endif %}
            <a href="/logout" class="btn-header">🚪 Выйти</a>
        </div>
    </div>
    
    <div class="container">
        <div class="tabs" id="tabs">
            {% for q in queries %}
            <button class="tab" onclick="loadQuery({{ q.id }})">{{ q.name }}</button>
            {% endfor %}
        </div>
        
        <div id="queryDescBlock" style="display: none;"><div class="query-desc"><h3 id="queryNameDisplay"></h3><p id="queryDescDisplay"></p></div></div>
        
        <div class="params-panel" id="paramsPanel" style="display: none;">
            <div id="dynamicParams" class="params-grid"></div>
            <div class="region-row">
                <div class="param-field region-select">
                    <label>🌍 Выберите сервер</label>
                    <select id="serverSelect">
                        <option value="">-- Выберите сервер --</option>
                        {% for s in servers %}
                        <option value="{{ s.id }}">{{ s.name }} ({{ s.code }}) - {{ s.type|upper }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="search-btn"><button onclick="executeQuery()">🔍 Выполнить запрос</button></div>
            </div>
        </div>
        
        <div class="results" id="results"><div class="info">📌 Выберите вкладку с запросом</div></div>
    </div>
    
    <div id="modalServers" class="modal"><div class="modal-content"><div class="modal-header"><h2>🖥 Управление серверами</h2><span class="close" onclick="closeModal('modalServers')">&times;</span></div><div class="modal-body"><div id="serversList"></div><button class="btn-add" onclick="showServerForm()">+ Добавить сервер</button><div id="serverForm" style="display:none;"><input type="hidden" id="serverId"><div class="form-group"><label>Тип БД</label><select id="serverDbType"><option value="nsi">НСИ</option><option value="sdbp">СДБП</option></select></div><div class="form-group"><label>Номер региона</label><input type="text" id="serverRegionCode"></div><div class="form-group"><label>Название региона</label><input type="text" id="serverRegionName"></div><div class="form-group"><label>Хост</label><input type="text" id="serverHost"></div><div class="form-group"><label>Database</label><input type="text" id="serverDatabase"></div><button class="btn-add" onclick="saveServer()">Сохранить</button><button onclick="hideServerForm()">Отмена</button></div></div></div></div>
    
    <div id="modalQueries" class="modal"><div class="modal-content"><div class="modal-header"><h2>📋 Управление запросами</h2><span class="close" onclick="closeModal('modalQueries')">&times;</span></div><div class="modal-body"><div id="queriesList"></div><button class="btn-add" onclick="showQueryForm()">+ Добавить запрос</button><div id="queryForm" style="display:none;"><input type="hidden" id="queryId"><div class="form-group"><label>Название</label><input type="text" id="queryName"></div><div class="form-group"><label>Описание</label><input type="text" id="queryDesc"></div><div class="form-group"><label>SQL запрос</label><textarea id="querySql" rows="6"></textarea></div><div class="form-group"><label>Тип сервера</label><select id="queryServerType"><option value="">Все</option><option value="nsi">НСИ</option><option value="sdbp">СДБП</option></select></div><button class="btn-add" onclick="saveQuery()">Сохранить</button><button onclick="hideQueryForm()">Отмена</button></div></div></div></div>
    
    <div id="modalUsers" class="modal"><div class="modal-content"><div class="modal-header"><h2>👥 Пользователи</h2><span class="close" onclick="closeModal('modalUsers')">&times;</span></div><div class="modal-body"><div id="usersList"></div><button class="btn-add" onclick="showUserForm()">+ Добавить пользователя</button><div id="userForm" style="display:none;"><input type="hidden" id="userId"><div class="form-group"><label>Логин</label><input type="text" id="userUsername"></div><div class="form-group"><div class="password-generate"><input type="text" id="userPassword" placeholder="Пароль"><button class="generate-btn" onclick="generateUserPassword()">🎲</button></div></div><div class="form-group"><label>Полное имя</label><input type="text" id="userFullName"></div><div class="form-group"><label>Роль</label><select id="userRole"><option value="user">Пользователь</option><option value="admin">Администратор</option></select></div><div class="form-group"><label>Доступ к серверам</label><div id="userServerAccess" class="access-checkboxes"></div></div><div class="form-group"><label>Доступ к запросам</label><div id="userQueryAccess" class="access-checkboxes"></div></div><button class="btn-add" onclick="saveUser()">Сохранить</button><button onclick="hideUserForm()">Отмена</button></div></div></div></div>
    
    <div id="modalLogs" class="modal"><div class="modal-content"><div class="modal-header"><h2>📜 Логи</h2><span class="close" onclick="closeModal('modalLogs')">&times;</span></div><div class="modal-body"><div id="logsList"></div></div></div></div>
    
    <div id="detailModal" class="modal"><div class="modal-content"><div class="modal-header"><h2>📋 Детальная информация</h2><span class="close" onclick="closeDetailModal()">&times;</span></div><div class="modal-body" id="detailModalContent"></div></div></div>
    
    <script>
        let currentQuery = null, currentResults = null, currentQueryId = null;
        
        function loadQuery(qid) {
            if (currentQueryId !== qid) clearResults();
            currentQueryId = qid;
            fetch('/api/query/' + qid).then(r => r.json()).then(d => {
                currentQuery = d;
                document.getElementById('queryDescBlock').style.display = 'block';
                document.getElementById('queryNameDisplay').innerText = d.name;
                document.getElementById('queryDescDisplay').innerText = d.description || '';
                renderParams(d.parameters);
                document.getElementById('paramsPanel').style.display = 'block';
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                event.target.classList.add('active');
            });
        }
        
        function renderParams(params) {
            let c = document.getElementById('dynamicParams');
            if (!params || params.length === 0) { c.innerHTML = '<div class="info">ℹ️ Без параметров</div>'; return; }
            let h = '';
            params.forEach(p => { h += `<div class="param-field"><label>${p.label}${p.required?'*':''}</label><input type="${p.type==='date'?'date':'text'}" id="param_${p.name}" placeholder="${p.placeholder||''}"></div>`; });
            c.innerHTML = h;
        }
        
        function clearResults() { document.getElementById('results').innerHTML = '<div class="info">📌 Результаты очищены</div>'; currentResults = null; }
        
        function executeQuery() {
            if (!currentQuery) { alert('Выберите вкладку'); return; }
            let sid = document.getElementById('serverSelect').value;
            if (!sid) { alert('Выберите сервер'); return; }
            let params = {};
            if (currentQuery.parameters) currentQuery.parameters.forEach(p => { let inp = document.getElementById('param_'+p.name); if(inp && inp.value) params[p.name]=inp.value; });
            document.getElementById('results').innerHTML = '<div class="loading">⏳ Выполнение...</div>';
            fetch('/api/execute', {
                method:'POST', headers:{'Content-Type':'application/json'},
                body:JSON.stringify({query_id:currentQuery.id, server_id:sid, parameters:params})
            }).then(r=>r.json()).then(d=>{
                if(d.error) document.getElementById('results').innerHTML = '<div class="error">'+d.error+'</div>';
                else if(d.results && d.results.length>0) { currentResults = d.results; displayResults(d.results); }
                else document.getElementById('results').innerHTML = '<div class="info">Ничего не найдено</div>';
            });
        }
        
        function displayResults(res) {
            let headers = Object.keys(res[0]);
            let html = `<div class="results-header"><div>✅ Найдено: ${res.length}</div><button class="export-btn" onclick="exportExcel()">📊 Excel</button></div><div style="overflow-x:auto;"><table><thead><tr>`;
            headers.forEach(h=>html+=`<th>${h}</th>`);
            html+=`</thead><tbody>`;
            res.forEach((r,i)=>{ html+=`<tr onclick="showDetail(${i})">`; headers.forEach(h=>html+=`<td>${r[h]||''}</td>`); html+=`</tr>`; });
            html+=`</tbody></table></div>`;
            document.getElementById('results').innerHTML = html;
        }
        
        function showDetail(i) {
            let r = currentResults[i];
            let html = '<table style="width:100%">';
            for(let [k,v] of Object.entries(r)) html += `<tr><td style="padding:8px;font-weight:bold">${k}<td style="padding:8px">${v||'Не указано'}`;
            html += '</table>';
            document.getElementById('detailModalContent').innerHTML = html;
            document.getElementById('detailModal').style.display = 'block';
        }
        function closeDetailModal() { document.getElementById('detailModal').style.display = 'none'; }
        
        function exportExcel() {
            if(!currentResults) return;
            fetch('/api/export_excel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({results:currentResults})})
            .then(r=>r.json()).then(d=>{ if(d.file_url) window.open(d.file_url); });
        }
        
        function openAdminServers() { document.getElementById('modalServers').style.display='block'; loadServers(); }
        function openAdminQueries() { document.getElementById('modalQueries').style.display='block'; loadQueries(); }
        function openAdminUsers() { document.getElementById('modalUsers').style.display='block'; loadUsers(); }
        function openAdminLogs() { document.getElementById('modalLogs').style.display='block'; loadLogs(); }
        function closeModal(id) { document.getElementById(id).style.display='none'; }
        
        function loadServers() {
            fetch('/api/admin/servers').then(r=>r.json()).then(d=>{
                let h=''; d.forEach(s=>{ h+=`<div class="card"><div><strong>${s.region_name} (${s.region_code})</strong><br><small>${s.host} | ${s.database_name}</small></div><div><button onclick="editServer(${s.id})">✏️</button><button onclick="deleteServer(${s.id})">🗑</button></div></div>`; });
                document.getElementById('serversList').innerHTML = h || '<p>Нет серверов</p>';
            });
        }
        function showServerForm() { document.getElementById('serverForm').style.display='block'; document.getElementById('serverId').value=''; document.getElementById('serverRegionCode').value=''; document.getElementById('serverRegionName').value=''; document.getElementById('serverHost').value=''; document.getElementById('serverDatabase').value=''; }
        function hideServerForm() { document.getElementById('serverForm').style.display='none'; loadServers(); }
        function editServer(id){ fetch('/api/admin/server/'+id).then(r=>r.json()).then(s=>{ document.getElementById('serverForm').style.display='block'; document.getElementById('serverId').value=s.id; document.getElementById('serverRegionCode').value=s.region_code; document.getElementById('serverRegionName').value=s.region_name; document.getElementById('serverHost').value=s.host; document.getElementById('serverDatabase').value=s.database_name; }); }
        function saveServer(){
            let data={ id:document.getElementById('serverId').value||null, db_type:document.getElementById('serverDbType').value, region_code:document.getElementById('serverRegionCode').value, region_name:document.getElementById('serverRegionName').value, host:document.getElementById('serverHost').value, database_name:document.getElementById('serverDatabase').value };
            fetch('/api/admin/save_server',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})
            .then(r=>r.json()).then(d=>{ if(d.success){ alert('Сохранено'); hideServerForm(); } else alert('Ошибка'); });
        }
        function deleteServer(id){ if(confirm('Удалить?')) fetch('/api/admin/delete_server/'+id,{method:'DELETE'}).then(()=>loadServers()); }
        
        function loadQueries(){
            fetch('/api/admin/queries').then(r=>r.json()).then(d=>{
                let h=''; d.forEach(q=>{ h+=`<div class="card"><div><strong>${q.name}</strong><br><small>${q.description||''}</small></div><div><button onclick="editQuery(${q.id})">✏️</button><button onclick="deleteQuery(${q.id})">🗑</button></div></div>`; });
                document.getElementById('queriesList').innerHTML = h || '<p>Нет запросов</p>';
            });
        }
        function showQueryForm(){ document.getElementById('queryForm').style.display='block'; document.getElementById('queryId').value=''; document.getElementById('queryName').value=''; document.getElementById('queryDesc').value=''; document.getElementById('querySql').value=''; document.getElementById('queryServerType').value=''; }
        function hideQueryForm(){ document.getElementById('queryForm').style.display='none'; loadQueries(); }
        function editQuery(id){ fetch('/api/query/'+id).then(r=>r.json()).then(q=>{ document.getElementById('queryForm').style.display='block'; document.getElementById('queryId').value=q.id; document.getElementById('queryName').value=q.name; document.getElementById('queryDesc').value=q.description||''; document.getElementById('querySql').value=q.sql_text; document.getElementById('queryServerType').value=q.server_type||''; }); }
        function saveQuery(){
            let data={ id:document.getElementById('queryId').value||null, name:document.getElementById('queryName').value, description:document.getElementById('queryDesc').value, sql_text:document.getElementById('querySql').value, parameters:[], server_type:document.getElementById('queryServerType').value };
            fetch('/api/admin/save_query',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})
            .then(r=>r.json()).then(d=>{ if(d.success){ alert('Сохранено'); hideQueryForm(); } else alert('Ошибка'); });
        }
        function deleteQuery(id){ if(confirm('Удалить?')) fetch('/api/admin/delete_query/'+id,{method:'DELETE'}).then(()=>loadQueries()); }
        
        function loadUsers(){
            fetch('/api/admin/users').then(r=>r.json()).then(d=>{
                let h=''; d.forEach(u=>{ h+=`<div class="card"><div><strong>${u.username}</strong> (${u.full_name})<br><small>${u.role}</small></div><div><button onclick="editUser(${u.id})">✏️</button>${u.username!=='admin'?`<button onclick="deleteUser(${u.id})">🗑</button>`:''}</div></div>`; });
                document.getElementById('usersList').innerHTML = h || '<p>Нет пользователей</p>';
            });
        }
        function generateUserPassword(){ fetch('/api/generate_password').then(r=>r.json()).then(d=>{ document.getElementById('userPassword').value=d.password; }); }
        function showUserForm(){ document.getElementById('userForm').style.display='block'; document.getElementById('userId').value=''; document.getElementById('userUsername').value=''; document.getElementById('userPassword').value=''; document.getElementById('userFullName').value=''; document.getElementById('userRole').value='user'; loadAccessCheckboxes(); }
        function hideUserForm(){ document.getElementById('userForm').style.display='none'; loadUsers(); }
        function loadAccessCheckboxes(){
            fetch('/api/admin/servers').then(r=>r.json()).then(s=>{ let h=''; s.forEach(ss=>{ h+=`<label><input type="checkbox" class="serverAccess" value="${ss.id}"> ${ss.region_name} (${ss.region_code})</label>`; }); document.getElementById('userServerAccess').innerHTML=h; });
            fetch('/api/admin/queries').then(r=>r.json()).then(q=>{ let h=''; q.forEach(qq=>{ h+=`<label><input type="checkbox" class="queryAccess" value="${qq.id}"> ${qq.name}</label>`; }); document.getElementById('userQueryAccess').innerHTML=h; });
        }
        function editUser(id){
            fetch('/api/admin/user/'+id).then(r=>r.json()).then(u=>{
                document.getElementById('userForm').style.display='block'; document.getElementById('userId').value=u.id; document.getElementById('userUsername').value=u.username; document.getElementById('userPassword').value=''; document.getElementById('userFullName').value=u.full_name; document.getElementById('userRole').value=u.role;
                fetch('/api/admin/servers').then(r=>r.json()).then(s=>{ let h=''; s.forEach(ss=>{ let checked=u.server_access.includes(ss.id)?'checked':''; h+=`<label><input type="checkbox" class="serverAccess" value="${ss.id}" ${checked}> ${ss.region_name} (${ss.region_code})</label>`; }); document.getElementById('userServerAccess').innerHTML=h; });
                fetch('/api/admin/queries').then(r=>r.json()).then(q=>{ let h=''; q.forEach(qq=>{ let checked=u.query_access.includes(qq.id)?'checked':''; h+=`<label><input type="checkbox" class="queryAccess" value="${qq.id}" ${checked}> ${qq.name}</label>`; }); document.getElementById('userQueryAccess').innerHTML=h; });
            });
        }
        function saveUser(){
            let serverAccess=[], queryAccess=[];
            document.querySelectorAll('.serverAccess:checked').forEach(cb=>serverAccess.push(parseInt(cb.value)));
            document.querySelectorAll('.queryAccess:checked').forEach(cb=>queryAccess.push(parseInt(cb.value)));
            let data={ id:document.getElementById('userId').value||null, username:document.getElementById('userUsername').value, password:document.getElementById('userPassword').value, full_name:document.getElementById('userFullName').value, role:document.getElementById('userRole').value, server_access:serverAccess, query_access:queryAccess };
            fetch('/api/admin/save_user',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})
            .then(r=>r.json()).then(d=>{ if(d.success){ alert(d.message); if(d.password_shown) alert('Пароль: '+d.password_shown); hideUserForm(); } else alert('Ошибка'); });
        }
        function deleteUser(id){ if(confirm('Удалить?')) fetch('/api/admin/delete_user/'+id,{method:'DELETE'}).then(()=>loadUsers()); }
        
        function loadLogs(){
            fetch('/api/admin/logs').then(r=>r.json()).then(d=>{
                let h='<table border="1"><tr><th>Дата</th><th>Пользователь</th><th>Действие</th><th>Детали</th></tr>';
                d.forEach(l=>{ h+=`<tr><td>${l.timestamp}</td><td>${l.username}</td><td>${l.action}</td><td>${l.details}</td></tr>`; });
                h+='</table>';
                document.getElementById('logsList').innerHTML = h;
            });
        }
        
        window.onclick = function(e) { if(e.target.classList.contains('modal')) e.target.style.display='none'; }
    </script>
    {% endif %}
</body>
</html>
'''

# ---------------------- API МАРШРУТЫ ----------------------
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        username = request.form.get('username')
        password = hashlib.sha256(request.form.get('password', '').encode()).hexdigest()
        user = db.execute_query("SELECT id, username, full_name, role FROM users WHERE username=%s AND password_hash=%s AND is_active=1", (username, password), fetch_one=True)
        if user:
            session['user'] = {'id': user['id'], 'username': user['username'], 'full_name': user['full_name'], 'role': user['role']}
            log_action(user['id'], user['username'], "login", "Вход в систему", request.remote_addr)
            return redirect(url_for('index'))
        return render_template_string(MAIN_TEMPLATE, error="Неверный логин или пароль", servers=[], queries=[])
    if not session.get('user'):
        return render_template_string(MAIN_TEMPLATE, servers=[], queries=[])
    servers = get_user_servers(session['user']['id'], session['user']['role'])
    queries = get_user_queries(session['user']['id'], session['user']['role'])
    return render_template_string(MAIN_TEMPLATE, session=session, servers=servers, queries=queries)

@app.route('/logout')
def logout():
    if session.get('user'):
        log_action(session['user']['id'], session['user']['username'], "logout", "Выход из системы", request.remote_addr)
    session.clear()
    return redirect(url_for('index'))

@app.route('/api/generate_password')
def api_generate_password():
    return jsonify({"password": generate_password()})

@app.route('/api/query/<int:query_id>')
def api_get_query(query_id):
    q = db.execute_query("SELECT id, name, description, sql_text, parameters, server_type FROM queries WHERE id=%s", (query_id,), fetch_one=True)
    if not q:
        return jsonify({"error": "Not found"}), 404
    params = json.loads(q['parameters']) if q['parameters'] else []
    return jsonify({"id": q['id'], "name": q['name'], "description": q['description'], "sql_text": q['sql_text'], "parameters": params, "server_type": q['server_type'] or ""})

@app.route('/api/execute', methods=['POST'])
def api_execute():
    if not session.get('user'):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    query_id = data.get('query_id')
    server_id = data.get('server_id')
    parameters = data.get('parameters', {})
    
    q = db.execute_query("SELECT name, sql_text FROM queries WHERE id=%s", (query_id,), fetch_one=True)
    if not q:
        return jsonify({"error": "Query not found"}), 404
    
    sql_text = q['sql_text']
    where_conditions = []
    params_for_execute = []
    
    if parameters.get('serial'):
        where_conditions.append("t.TerminalSerialNumber LIKE %s")
        params_for_execute.append(f"%{parameters['serial']}%")
    if parameters.get('tuid'):
        where_conditions.append("JSON_UNQUOTE(JSON_EXTRACT(t.TerminalConfig, '$.EMV.OfflineTkpTerminalId')) LIKE %s")
        params_for_execute.append(f"%{parameters['tuid']}%")
    if parameters.get('bank_tid'):
        where_conditions.append("e.ID LIKE %s")
        params_for_execute.append(f"%{parameters['bank_tid']}%")
    
    if not where_conditions:
        return jsonify({"error": "Заполните хотя бы одно поле"}), 400
    
    where_clause = " AND ".join(where_conditions)
    final_sql = sql_text.replace("{where_conditions}", where_clause)
    
    db_conn, error = get_db_connection(server_id)
    if error:
        return jsonify({"error": error}), 500
    try:
        with db_conn.cursor() as cursor:
            cursor.execute(final_sql, params_for_execute)
            results = cursor.fetchall()
        db_conn.close()
        log_action(session['user']['id'], session['user']['username'], "execute_query", f"Запрос ID={query_id}", request.remote_addr)
        for i, row in enumerate(results, 1):
            row['№'] = i
        return jsonify({"results": results, "count": len(results)})
    except Exception as e:
        db_conn.close()
        return jsonify({"error": str(e)}), 500

@app.route('/api/export_excel', methods=['POST'])
def api_export_excel():
    if not session.get('user'):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    results = data.get('results', [])
    if not results:
        return jsonify({"error": "Нет данных"}), 400
    try:
        import openpyxl, os
        wb = openpyxl.Workbook()
        ws = wb.active
        headers = list(results[0].keys())
        for c, h in enumerate(headers, 1):
            ws.cell(row=1, column=c, value=h)
        for r, row in enumerate(results, 2):
            for c, h in enumerate(headers, 1):
                ws.cell(row=r, column=c, value=str(row.get(h, '')))
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"export_{ts}.xlsx"
        path = os.path.join(os.path.dirname(__file__), fname)
        wb.save(path)
        return jsonify({"file_url": f"/download/{fname}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    from flask import send_file
    import os
    return send_file(os.path.join(os.path.dirname(__file__), filename), as_attachment=True)

# ----- АДМИН API -----
@app.route('/api/admin/servers')
def api_admin_servers():
    if not session.get('user') or session['user']['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    srv = db.execute_query("SELECT id, region_code, region_name, host, database_name, db_type FROM servers", fetch_all=True) or []
    return jsonify([{"id": s['id'], "region_code": s['region_code'], "region_name": s['region_name'], "host": s['host'], "database_name": s['database_name'], "db_type": s['db_type']} for s in srv])

@app.route('/api/admin/server/<int:server_id>')
def api_admin_server(server_id):
    if not session.get('user') or session['user']['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    s = db.execute_query("SELECT id, region_code, region_name, host, database_name, db_type FROM servers WHERE id=%s", (server_id,), fetch_one=True)
    return jsonify({"id": s['id'], "region_code": s['region_code'], "region_name": s['region_name'], "host": s['host'], "database_name": s['database_name'], "db_type": s['db_type']})

@app.route('/api/admin/save_server', methods=['POST'])
def api_admin_save_server():
    if not session.get('user') or session['user']['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    d = request.json
    try:
        if d.get('id'):
            db.execute_query("UPDATE servers SET region_code=%s, region_name=%s, host=%s, database_name=%s, db_type=%s WHERE id=%s", (d['region_code'], d['region_name'], d['host'], d['database_name'], d['db_type'], d['id']))
        else:
            db.execute_query("INSERT INTO servers (region_code, region_name, host, database_name, db_type) VALUES (%s, %s, %s, %s, %s)", (d['region_code'], d['region_name'], d['host'], d['database_name'], d['db_type']))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/admin/delete_server/<int:server_id>', methods=['DELETE'])
def api_admin_delete_server(server_id):
    if not session.get('user') or session['user']['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    db.execute_query("DELETE FROM servers WHERE id=%s", (server_id,))
    db.execute_query("DELETE FROM user_server_access WHERE server_id=%s", (server_id,))
    return jsonify({"success": True})

@app.route('/api/admin/queries')
def api_admin_queries():
    if not session.get('user') or session['user']['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    q = db.execute_query("SELECT id, name, description FROM queries", fetch_all=True) or []
    return jsonify([{"id": qq['id'], "name": qq['name'], "description": qq['description']} for qq in q])

@app.route('/api/admin/save_query', methods=['POST'])
def api_admin_save_query():
    if not session.get('user') or session['user']['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    d = request.json
    params_json = json.dumps(d.get('parameters', []))
    try:
        if d.get('id'):
            db.execute_query("UPDATE queries SET name=%s, description=%s, sql_text=%s, parameters=%s, server_type=%s WHERE id=%s", (d['name'], d.get('description', ''), d['sql_text'], params_json, d.get('server_type', ''), d['id']))
        else:
            db.execute_query("INSERT INTO queries (name, description, sql_text, parameters, server_type, created_by) VALUES (%s, %s, %s, %s, %s, %s)", (d['name'], d.get('description', ''), d['sql_text'], params_json, d.get('server_type', ''), session['user']['id']))
        log_action(session['user']['id'], session['user']['username'], "save_query", f"Сохранен запрос {d['name']}", request.remote_addr)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/admin/delete_query/<int:query_id>', methods=['DELETE'])
def api_admin_delete_query(query_id):
    if not session.get('user') or session['user']['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    db.execute_query("DELETE FROM queries WHERE id=%s", (query_id,))
    db.execute_query("DELETE FROM user_query_access WHERE query_id=%s", (query_id,))
    return jsonify({"success": True})

@app.route('/api/admin/users')
def api_admin_users():
    if not session.get('user') or session['user']['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    u = db.execute_query("SELECT id, username, full_name, role FROM users", fetch_all=True) or []
    return jsonify([{"id": uu['id'], "username": uu['username'], "full_name": uu['full_name'], "role": uu['role']} for uu in u])

@app.route('/api/admin/user/<int:user_id>')
def api_admin_user(user_id):
    if not session.get('user') or session['user']['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    u = db.execute_query("SELECT id, username, full_name, role FROM users WHERE id=%s", (user_id,), fetch_one=True)
    server_acc = db.execute_query("SELECT server_id FROM user_server_access WHERE user_id=%s", (user_id,), fetch_all=True) or []
    query_acc = db.execute_query("SELECT query_id FROM user_query_access WHERE user_id=%s", (user_id,), fetch_all=True) or []
    return jsonify({"id": u['id'], "username": u['username'], "full_name": u['full_name'], "role": u['role'], "server_access": [a['server_id'] for a in server_acc], "query_access": [a['query_id'] for a in query_acc]})

@app.route('/api/admin/save_user', methods=['POST'])
def api_admin_save_user():
    if not session.get('user') or session['user']['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    d = request.json
    password_shown = None
    try:
        if d.get('id'):
            if d.get('password') and d['password'].strip():
                ph = hashlib.sha256(d['password'].encode()).hexdigest()
                db.execute_query("UPDATE users SET username=%s, password_hash=%s, full_name=%s, role=%s WHERE id=%s", (d['username'], ph, d['full_name'], d['role'], d['id']))
            else:
                db.execute_query("UPDATE users SET username=%s, full_name=%s, role=%s WHERE id=%s", (d['username'], d['full_name'], d['role'], d['id']))
            db.execute_query("DELETE FROM user_server_access WHERE user_id=%s", (d['id'],))
            for sid in d.get('server_access', []):
                db.execute_query("INSERT INTO user_server_access (user_id, server_id, can_view) VALUES (%s, %s, 1)", (d['id'], sid))
            db.execute_query("DELETE FROM user_query_access WHERE user_id=%s", (d['id'],))
            for qid in d.get('query_access', []):
                db.execute_query("INSERT INTO user_query_access (user_id, query_id, can_view) VALUES (%s, %s, 1)", (d['id'], qid))
            msg = "Обновлено"
        else:
            if not d.get('password'):
                return jsonify({"error": "Пароль обязателен"}), 400
            ph = hashlib.sha256(d['password'].encode()).hexdigest()
            uid = db.execute_query("INSERT INTO users (username, password_hash, full_name, role) VALUES (%s, %s, %s, %s)", (d['username'], ph, d['full_name'], d['role']))
            for sid in d.get('server_access', []):
                db.execute_query("INSERT INTO user_server_access (user_id, server_id, can_view) VALUES (%s, %s, 1)", (uid, sid))
            for qid in d.get('query_access', []):
                db.execute_query("INSERT INTO user_query_access (user_id, query_id, can_view) VALUES (%s, %s, 1)", (uid, qid))
            password_shown = d['password']
            msg = "Создан"
        log_action(session['user']['id'], session['user']['username'], "save_user", f"Пользователь {d['username']}", request.remote_addr)
        res = {"success": True, "message": msg}
        if password_shown:
            res["password_shown"] = password_shown
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/admin/delete_user/<int:user_id>', methods=['DELETE'])
def api_admin_delete_user(user_id):
    if not session.get('user') or session['user']['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    u = db.execute_query("SELECT username FROM users WHERE id=%s", (user_id,), fetch_one=True)
    if u and u['username'] == 'admin':
        return jsonify({"error": "Нельзя удалить админа"}), 400
    db.execute_query("DELETE FROM users WHERE id=%s", (user_id,))
    db.execute_query("DELETE FROM user_server_access WHERE user_id=%s", (user_id,))
    db.execute_query("DELETE FROM user_query_access WHERE user_id=%s", (user_id,))
    return jsonify({"success": True})

@app.route('/api/admin/logs')
def api_admin_logs():
    if not session.get('user') or session['user']['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    logs = db.execute_query("SELECT id, username, action, details, timestamp FROM logs ORDER BY id DESC LIMIT 200", fetch_all=True) or []
    return jsonify([{"id": l['id'], "username": l['username'], "action": l['action'], "details": l['details'], "timestamp": l['timestamp']} for l in logs])

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 ВЕБ-ПРИЛОЖЕНИЕ ЗАПУЩЕНО")
    print("📱 http://" + "186.246.2.145" + ":8080")
    print("👤 admin / admin123")
    print("="*60 + "\n")
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)
