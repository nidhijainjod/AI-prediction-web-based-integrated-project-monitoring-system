from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField
from wtforms.validators import DataRequired, Email, Length, Optional

from app.models import ROLE_ADMIN, ROLE_MANAGER


class UserForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=150)])
    role = SelectField("Role", choices=[(ROLE_MANAGER, "Manager"), (ROLE_ADMIN, "Administrator")])
    password = PasswordField(
        "Password", validators=[Optional(), Length(min=6, message="Password must be at least 6 characters.")]
    )
    is_active_flag = BooleanField("Active", default=True)
