from django.core.management.base import BaseCommand
from django.db import connections
from devices.models import TestMetric, TestRun, BloodAnalyzer, DataSource
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.utils import timezone
import random
from datetime import datetime, timedelta
import uuid
import logging
import os

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Populates factory databases with blood analyzer devices'

    def handle(self, *args, **options):
        # Initialize data sources
        self.data_source_ids = {}
        for db_name in ['factory_a', 'factory_c']:
            # Create data source in default database if it doesn't exist
            with connections['default'].cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM devices_datasource 
                    WHERE name = %s AND source_type = 'factory'
                """, [db_name])
                result = cursor.fetchone()
                if result:
                    self.data_source_ids[db_name] = result[0]
                else:
                    # Create new data source
                    cursor.execute("""
                        INSERT INTO devices_datasource (name, source_type, is_active)
                        VALUES (%s, 'factory', 1)
                    """, [db_name])
                    cursor.execute("SELECT last_insert_rowid()")
                    self.data_source_ids[db_name] = cursor.fetchone()[0]
                    self.stdout.write(f"Created data source for {db_name}")

        # Clear existing data
        for db_name in ['factory_a', 'factory_c']:
            with connections[db_name].cursor() as cursor:
                # Clear test metrics
                cursor.execute("DELETE FROM devices_testmetric")
                self.stdout.write(f"Cleared test metrics from {db_name} database")
                
                # Clear test runs
                cursor.execute("DELETE FROM devices_testrun")
                self.stdout.write(f"Cleared test runs from {db_name} database")
                
                # Clear blood analyzers
                cursor.execute("DELETE FROM devices_bloodanalyzer")
                self.stdout.write(f"Cleared blood analyzers from {db_name} database")
                
                # Add data_source_id column if it doesn't exist
                cursor.execute("""
                    SELECT sql FROM sqlite_master 
                    WHERE type='table' AND name='devices_bloodanalyzer'
                """)
                create_sql = cursor.fetchone()[0]
                if 'data_source_id' not in create_sql:
                    cursor.execute("ALTER TABLE devices_bloodanalyzer ADD COLUMN data_source_id INTEGER NOT NULL DEFAULT 0")
                    self.stdout.write(f"Added data_source_id column to devices_bloodanalyzer in {db_name}")
                
                # Clear users except superuser
                cursor.execute("DELETE FROM auth_user WHERE is_superuser = 0")
                self.stdout.write(f"Cleared users from {db_name} database")

        # Create devices for each factory
        for db_name in ['factory_a', 'factory_c']:
            try:
                with connections[db_name].cursor() as cursor:
                    # Create a technician user
                    user_params = [
                        f'tech_{db_name}',
                        'pbkdf2_sha256$600000$dummy$dummy=',  # Dummy password hash
                        0,  # is_superuser
                        1,  # is_staff
                        1,  # is_active
                        timezone.now().isoformat(),
                        'Factory',
                        'Technician',
                        f'tech@{db_name}.com'
                    ]
                    
                    cursor.execute("""
                        INSERT INTO auth_user (
                            username, password, is_superuser, is_staff, is_active,
                            date_joined, first_name, last_name, email
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, user_params)
                    
                    self.stdout.write(f"Created technician user for {db_name}")
                    
                    # Get the technician ID
                    cursor.execute("SELECT id FROM auth_user WHERE username = %s", [f'tech_{db_name}'])
                    tech_id = cursor.fetchone()[0]
                    
                    # Create 5 blood analyzers
                    for i in range(1, 6):
                        device_id = f"{db_name.upper()}-BA-{i:03d}"
                        now = timezone.now()
                        
                        device_params = [
                            device_id,
                            'Hematology',
                            'Active',
                            (now - timedelta(days=30)).isoformat(),
                            (now + timedelta(days=30)).isoformat(),
                            f'Lab {i}',
                            (now - timedelta(days=365)).date().isoformat(),
                            tech_id
                        ]
                        
                        self.stdout.write(f"Inserting device with params: {device_params}")
                        
                        cursor.execute("""
                            INSERT INTO devices_bloodanalyzer (
                                device_id, device_type, status, last_calibration,
                                next_calibration_due, location, manufacturing_date,
                                assigned_technician_id, data_source_id
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, device_params + [self.data_source_ids[db_name]])
                    
                    self.stdout.write(f"Successfully populated {db_name} with devices")
                    
            except Exception as e:
                self.stdout.write(f"Error populating {db_name} devices: {str(e)}")
                logger.error(f"Error populating {db_name} devices", exc_info=True)

    def create_factory_technicians(self):
        # Create technicians in default database
        factory_a_tech = User.objects.using('default').create(
            username='factory_a_tech',
            password=make_password('password123'),  # Set a default password
            email='tech_a@factory.com',
            first_name='Tech',
            last_name='A',
            is_staff=True,
            is_active=True,
            date_joined=timezone.now()
        )

        factory_c_tech = User.objects.using('default').create(
            username='factory_c_tech',
            password=make_password('password123'),  # Set a default password
            email='tech_c@factory.com',
            first_name='Tech',
            last_name='C',
            is_staff=True,
            is_active=True,
            date_joined=timezone.now()
        )

        # Create technician in Factory A database
        with connections['factory_a'].cursor() as cursor:
            cursor.execute("""
                INSERT INTO auth_user (
                    id, password, last_login, is_superuser, username, first_name,
                    last_name, email, is_staff, is_active, date_joined
                ) VALUES (%s, %s, NULL, 0, %s, %s, %s, %s, 1, 1, %s)
            """, [
                factory_a_tech.id,
                factory_a_tech.password,
                factory_a_tech.username,
                factory_a_tech.first_name,
                factory_a_tech.last_name,
                factory_a_tech.email,
                factory_a_tech.date_joined.isoformat()
            ])
            print("Created technician in Factory A database")

        # Create technician in Factory C database
        with connections['factory_c'].cursor() as cursor:
            cursor.execute("""
                INSERT INTO auth_user (
                    id, password, last_login, is_superuser, username, first_name,
                    last_name, email, is_staff, is_active, date_joined
                ) VALUES (%s, %s, NULL, 0, %s, %s, %s, %s, 1, 1, %s)
            """, [
                factory_c_tech.id,
                factory_c_tech.password,
                factory_c_tech.username,
                factory_c_tech.first_name,
                factory_c_tech.last_name,
                factory_c_tech.email,
                factory_c_tech.date_joined.isoformat()
            ])
            print("Created technician in Factory C database")

        return factory_a_tech

    def create_factory_devices(self, factory_name, num_devices, technician, data_source):
        devices = []

        # First, ensure the technician exists in the target database
        with connections[factory_name].cursor() as cursor:
            cursor.execute("SELECT id FROM auth_user WHERE id = %s", [technician.id])
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO auth_user (
                        id, password, last_login, is_superuser, username, first_name,
                        last_name, email, is_staff, is_active, date_joined
                    ) VALUES (%s, %s, NULL, 0, %s, %s, %s, %s, 1, 1, %s)
                """, [
                    technician.id,
                    technician.password,
                    technician.username,
                    technician.first_name,
                    technician.last_name,
                    technician.email,
                    technician.date_joined.isoformat()
                ])
                print(f"Created technician in {factory_name} database")

        for i in range(num_devices):
            device_id = str(uuid.uuid4())
            mfg_date = timezone.now() - timedelta(days=random.randint(1, 365))
            cal_date = mfg_date + timedelta(days=random.randint(1, 30))
            next_cal_date = cal_date + timedelta(days=30)

            # Create device in factory database
            with connections[factory_name].cursor() as cursor:
                cursor.execute("""
                    INSERT INTO devices_bloodanalyzer (
                        device_id, device_type, status, location,
                        manufacturing_date, last_calibration, next_calibration_due,
                        assigned_technician_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    device_id,
                    'production',  # device_type
                    'active',  # status
                    f'{factory_name.replace("_", " ").title()} Line {i+1}',  # location
                    mfg_date.date().isoformat(),
                    cal_date.isoformat(),
                    next_cal_date.isoformat(),
                    technician.id
                ])

            # Create corresponding device in default database
            device = BloodAnalyzer.objects.using('default').create(
                device_id=device_id,
                device_type='production',
                status='active',
                location=f'{factory_name.replace("_", " ").title()} Line {i+1}',
                manufacturing_date=mfg_date.date(),
                last_calibration=cal_date,
                next_calibration_due=next_cal_date,
                assigned_technician=technician,
                data_source=data_source
            )
            devices.append(device)

        print(f"Created {num_devices} devices in {factory_name}")
        return devices 