// Инициализация администратора в базе данных admin
db = db.getSiblingDB('admin');
db.createUser({
	user: 'admin',
	pwd: 'admin',
	roles: [
		{ role: 'root', db: 'admin' }
	]
});

// Инициализация пользователя в базе данных users_db
db = db.getSiblingDB('users_db');
db.createUser({
	user: 'admin',
	pwd: 'admin',
	roles: [
		{ role: 'readWrite', db: 'users_db' }
	]
});
