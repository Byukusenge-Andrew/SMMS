"""
Data Isolation and Security Audit for SMMS
This module performs comprehensive checks to ensure client data segregation
"""

import logging
from django.db import models
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.apps import apps

logger = logging.getLogger(__name__)


class DataIsolationAuditor:
    """Audits models and views for proper data isolation"""
    
    def __init__(self):
        self.user_dependent_models = []
        self.potential_security_issues = []
        self.warnings = []
        
    def audit_models(self):
        """Audit all models for proper user relationships"""
        
        # Get all installed apps
        app_models = []
        for app_config in apps.get_app_configs():
            if app_config.name.startswith('apps.'):
                app_models.extend(app_config.get_models())
        
        for model in app_models:
            self._audit_model(model)
            
    def _audit_model(self, model):
        """Audit a single model for user relationship"""
        model_name = f"{model._meta.app_label}.{model._meta.model_name}"
        
        # Check if model has user field
        has_user_field = False
        user_field_type = None
        
        for field in model._meta.fields:
            if field.name in ['user', 'owner', 'creator'] and isinstance(field, (models.ForeignKey, models.OneToOneField)):
                if field.related_model == User:
                    has_user_field = True
                    user_field_type = type(field).__name__
                    self.user_dependent_models.append({
                        'model': model_name,
                        'field_type': user_field_type,
                        'on_delete': getattr(field, 'on_delete', None).__name__ if hasattr(field, 'on_delete') else 'N/A'
                    })
                    break
        
        # Check for models that should probably have user fields
        sensitive_model_patterns = [
            'post', 'media', 'social', 'account', 'profile', 'notification', 
            'message', 'analytics', 'template', 'campaign', 'team'
        ]
        
        model_lower = model._meta.model_name.lower()
        if any(pattern in model_lower for pattern in sensitive_model_patterns):
            if not has_user_field:
                # Check if it's related to user through other means
                has_indirect_user = self._check_indirect_user_relationship(model)
                if not has_indirect_user:
                    self.potential_security_issues.append({
                        'model': model_name,
                        'issue': 'No direct or indirect user relationship found',
                        'severity': 'HIGH' if any(p in model_lower for p in ['post', 'media', 'social']) else 'MEDIUM'
                    })
    
    def _check_indirect_user_relationship(self, model):
        """Check if model has indirect relationship to User through other models"""
        for field in model._meta.fields:
            if isinstance(field, (models.ForeignKey, models.OneToOneField)):
                related_model = field.related_model
                if related_model != User:  # Not direct user relationship
                    # Check if related model has user field
                    for related_field in related_model._meta.fields:
                        if (related_field.name in ['user', 'owner', 'creator'] and 
                            isinstance(related_field, (models.ForeignKey, models.OneToOneField)) and
                            related_field.related_model == User):
                            return True
        return False
    
    def generate_report(self):
        """Generate comprehensive security audit report"""
        report = []
        
        report.append("=" * 80)
        report.append("SMMS DATA ISOLATION SECURITY AUDIT REPORT")
        report.append("=" * 80)
        report.append("")
        
        # User-dependent models
        report.append("USER-DEPENDENT MODELS:")
        report.append("-" * 40)
        for model_info in self.user_dependent_models:
            report.append(f"✓ {model_info['model']} ({model_info['field_type']}, on_delete={model_info['on_delete']})")
        report.append("")
        
        # Security issues
        if self.potential_security_issues:
            report.append("POTENTIAL SECURITY ISSUES:")
            report.append("-" * 40)
            for issue in self.potential_security_issues:
                severity_indicator = "⚠️" if issue['severity'] == 'HIGH' else "⚡"
                report.append(f"{severity_indicator} {issue['model']}: {issue['issue']} [{issue['severity']}]")
        else:
            report.append("✓ NO CRITICAL SECURITY ISSUES FOUND")
        report.append("")
        
        # Warnings
        if self.warnings:
            report.append("WARNINGS:")
            report.append("-" * 40)
            for warning in self.warnings:
                report.append(f"⚠️  {warning}")
        report.append("")
        
        return "\n".join(report)


class Command(BaseCommand):
    help = 'Audit data isolation and security for SMMS'
    
    def handle(self, *args, **options):
        auditor = DataIsolationAuditor()
        auditor.audit_models()
        
        report = auditor.generate_report()
        self.stdout.write(report)
        
        # Log report to file as well
        with open('security_audit_report.txt', 'w', encoding='utf-8') as f:
            f.write(report)
        
        self.stdout.write(
            self.style.SUCCESS(f'\nAudit complete! Found {len(auditor.user_dependent_models)} user-dependent models.')
        )
        
        if auditor.potential_security_issues:
            high_severity = [i for i in auditor.potential_security_issues if i['severity'] == 'HIGH']
            if high_severity:
                self.stdout.write(
                    self.style.ERROR(f'⚠️  {len(high_severity)} HIGH SEVERITY security issues found!')
                )
