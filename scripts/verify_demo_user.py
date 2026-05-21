import sqlite3
conn = sqlite3.connect('payments.db')
c = conn.cursor()
res = c.execute("UPDATE users SET email_verified=1 WHERE username='demo' OR email='demo@advancia.com'")
conn.commit()
print('rows affected:', c.rowcount)
conn.close()
