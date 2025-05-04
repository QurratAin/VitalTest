from django.db import models
from django.core.exceptions import FieldDoesNotExist

class DataSourceRouter:
    """
    A router to control all database operations on models in the devices application.
    """
    factory_models = ['bloodanalyzer', 'testrun', 'testmetric']  # Models that should exist in factory DBs
    system_models = ['synclog', 'datasource']  # Models that should only exist in default DB
    
    def db_for_read(self, model, **hints):
        """
        Attempts to read devices models go to the appropriate database.
        """
        if model._meta.app_label == 'devices':
            model_name = model._meta.model_name.lower()
            
            # System models should only be read from default database
            if model_name in self.system_models:
                return 'default'
                
            # Factory-specific models
            if model_name in self.factory_models:
                instance = hints.get('instance', None)
                if instance:
                    # Special handling for TestMetric
                    if model_name == 'testmetric':
                        if hasattr(instance, 'test_run') and instance.test_run:
                            return self.db_for_read(instance.test_run.__class__, instance=instance.test_run)
                        return 'default'
                        
                    # For other factory models, check data_source
                    try:
                        data_source_field = model._meta.get_field('data_source')
                        if data_source_field:
                            data_source_id = instance._state.fields_cache.get('data_source_id')
                            if data_source_id:
                                from devices.models import DataSource
                                try:
                                    data_source = DataSource.objects.using('default').get(id=data_source_id)
                                    if data_source.name == 'Factory A':
                                        return 'factory_a'
                                    elif data_source.name == 'Factory C':
                                        return 'factory_c'
                                except DataSource.DoesNotExist:
                                    pass
                    except FieldDoesNotExist:
                        pass
        return 'default'

    def db_for_write(self, model, **hints):
        """
        Attempts to write devices models go to the appropriate database.
        """
        if model._meta.app_label == 'devices':
            model_name = model._meta.model_name.lower()
            
            # System models should only be written to default database
            if model_name in self.system_models:
                return 'default'
                
            # Factory-specific models
            if model_name in self.factory_models:
                instance = hints.get('instance', None)
                if instance:
                    # Special handling for TestMetric
                    if model_name == 'testmetric':
                        if hasattr(instance, 'test_run') and instance.test_run:
                            return self.db_for_write(instance.test_run.__class__, instance=instance.test_run)
                        return 'default'
                        
                    # For other factory models, check data_source
                    try:
                        data_source_field = model._meta.get_field('data_source')
                        if data_source_field:
                            data_source_id = instance._state.fields_cache.get('data_source_id')
                            if data_source_id:
                                from devices.models import DataSource
                                try:
                                    data_source = DataSource.objects.using('default').get(id=data_source_id)
                                    if data_source.name == 'Factory A':
                                        return 'factory_a'
                                    elif data_source.name == 'Factory C':
                                        return 'factory_c'
                                except DataSource.DoesNotExist:
                                    pass
                    except FieldDoesNotExist:
                        pass
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if:
        1. Both objects are in the same database
        2. One object is a system model (in default DB) and the other is a factory model
        3. Both objects are auth.User (which should be in default DB)
        """
        if obj1._meta.app_label == 'devices' and obj2._meta.app_label == 'devices':
            model1 = obj1._meta.model_name.lower()
            model2 = obj2._meta.model_name.lower()
            
            # Both are system models
            if model1 in self.system_models and model2 in self.system_models:
                return True
                
            # Both are factory models
            if model1 in self.factory_models and model2 in self.factory_models:
                # Check if they belong to the same factory
                source1 = obj1._state.fields_cache.get('data_source_id')
                source2 = obj2._state.fields_cache.get('data_source_id')
                return source1 == source2
                
            # One is system, one is factory
            if (model1 in self.system_models and model2 in self.factory_models) or \
               (model1 in self.factory_models and model2 in self.system_models):
                return True
                
        # Allow relations between auth.User and any other model
        if obj1._meta.app_label == 'auth' or obj2._meta.app_label == 'auth':
            return True
            
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Control which models get migrated to which databases:
        - System models only migrate to default database
        - Factory-specific models migrate to both default and factory databases
        """
        if app_label == 'devices':
            if model_name:
                model_name = model_name.lower()
                if model_name in self.system_models:
                    return db == 'default'  # Only migrate to default database
                elif model_name in self.factory_models:
                    return True  # Migrate to all databases
            return db == 'default'  # Default behavior for other models
        return None 