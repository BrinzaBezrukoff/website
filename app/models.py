import hashlib

from flask_login import UserMixin

from app import db, login_manager


permissions_roles = db.Table("permissions_roles",
                             db.Column("role_id", db.Integer, db.ForeignKey("role.id")),
                             db.Column("permission_id", db.Integer, db.ForeignKey("permission.id"))
                             )


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True)
    display_name = db.Column(db.String(255))

    permissions = db.relationship("Permission", secondary=permissions_roles, lazy="dynamic",
                                  backref=db.backref("roles", lazy="dynamic"))

    def __repr__(self):
        return f"Role({self.name})"

    def has_permission(self, permission_name):
        return permission_name in [p.name for p in self.permissions.all()]

    @classmethod
    def new(cls, name, display_name, perms=tuple()):
        r = Role(name=name, display_name=display_name)
        for p_name in perms:
            p = Permission.query.filter(Permission.name == p_name).first()
            if not p:
                continue
            r.permissions.append(p)
        db.session.add(r)
        return r


class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    description = db.Column(db.String(255))

    def __repr__(self):
        return f"Permission({self.name})"

    @staticmethod
    def register(name, description, add_to_default=False):
        p = Permission.query.filter(Permission.name == name).first()
        if not p:
            p = Permission(name=name, description=description)
            db.session.add(p)
        if add_to_default:
            User.default_role.permissions.add(p)

    @staticmethod
    def register_many(perms, add_to_default=False):
        for name, desc in perms:
            Permission.register(name, desc, add_to_default=add_to_default)
        db.session.commit()


roles_users = db.Table("roles_users",
                       db.Column("user_id", db.Integer, db.ForeignKey("user.id")),
                       db.Column("role_id", db.Integer, db.ForeignKey("role.id"))
                       )


class User (db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255))
    profile_name = db.Column(db.String(255))
    password = db.Column(db.String(255))

    roles = db.relationship("Role", secondary=roles_users, lazy="dynamic",
                            backref=db.backref("users", lazy="dynamic"))

    def __init__(self, *args, **kwargs):
        super(db.Model, self).__init__(*args, **kwargs)
        super(UserMixin, self).__init__()

    def __repr__(self):
        return f"User({self.username})"

    def has_permission(self, permission_name):
        for r in self.roles.all():
            if r.has_permission(permission_name):
                return True
        return False

    def has_role(self, role_name):
        return role_name in [r.name for r in self.roles.all()]

    def set_role(self, role_name):
        r = Role.query.filter(Role.name == role_name).first()
        if r:
            self.roles.append(r)

    def set_password(self, password):
        self.password = User.hash_password(password)

    def check_password(self, password):
        return self.password == User.hash_password(password)

    @classmethod
    def new(cls, username, profile_name, password):
        u = User(username=username, profile_name=profile_name)
        u.set_password(password)
        return u

    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    @staticmethod
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)
