from django.db import migrations
from django.conf import settings
import secrets

def generate_token_key():
    return secrets.token_hex(20)

def create_tokens(apps, schema_editor):
    Token = apps.get_model('authtoken', 'Token')
    User = apps.get_model('auth', 'User')
    
    # Create tokens only for users that don't have one
    for user in User.objects.all():
        if not Token.objects.filter(user=user).exists():
            # Generate a unique key for the token
            key = generate_token_key()
            # Ensure the key doesn't already exist
            while Token.objects.filter(key=key).exists():
                key = generate_token_key()
            Token.objects.create(user=user, key=key)

def remove_tokens(apps, schema_editor):
    Token = apps.get_model('authtoken', 'Token')
    Token.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('devices', '0002_alter_bloodanalyzer_options_and_more'),
        ('authtoken', '0004_alter_tokenproxy_options'),
    ]

    operations = [
        migrations.RunPython(create_tokens, remove_tokens),
    ] 