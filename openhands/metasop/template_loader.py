"""
MetaSOP Template Loader

Provides a clean, robust mechanism for loading and managing MetaSOP templates.
This addresses the template loading issues identified in the analysis.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from openhands.metasop.models import SopTemplate, SopStep
import logging

logger = logging.getLogger(__name__)

class TemplateLoader:
    """Handles loading and caching of MetaSOP templates."""
    
    def __init__(self, templates_dir: Optional[str] = None):
        """Initialize template loader.
        
        Args:
            templates_dir: Path to templates directory. Defaults to sops/ directory.
        """
        if templates_dir is None:
            # Default to the sops directory in the metasop package
            current_dir = Path(__file__).parent
            templates_dir = current_dir / "sops"
        
        self.templates_dir = Path(templates_dir)
        self._template_cache: Dict[str, SopTemplate] = {}
        
    def load_template(self, template_name: str) -> SopTemplate:
        """Load a template by name.
        
        Args:
            template_name: Name of the template to load (e.g., 'feature_delivery')
            
        Returns:
            SopTemplate: The loaded template
            
        Raises:
            FileNotFoundError: If template file doesn't exist
            ValueError: If template is invalid
        """
        if template_name in self._template_cache:
            return self._template_cache[template_name]
            
        template_file = self.templates_dir / f"{template_name}.yaml"
        
        if not template_file.exists():
            raise FileNotFoundError(f"Template '{template_name}' not found at {template_file}")
            
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                template_data = yaml.safe_load(f)
                
            # Validate and create template
            template = self._create_template_from_data(template_data)
            self._template_cache[template_name] = template
            
            logger.info(f"Loaded template '{template_name}' with {len(template.steps)} steps")
            return template
            
        except Exception as e:
            logger.error(f"Failed to load template '{template_name}': {e}")
            raise ValueError(f"Invalid template '{template_name}': {e}")
    
    def _create_template_from_data(self, data: dict) -> SopTemplate:
        """Create SopTemplate from YAML data.
        
        Args:
            data: Template data from YAML file
            
        Returns:
            SopTemplate: Created template
        """
        if 'name' not in data or 'steps' not in data:
            raise ValueError("Template must have 'name' and 'steps' fields")
            
        steps = []
        for step_data in data['steps']:
            step = SopStep(
                id=step_data['id'],
                role=step_data['role'],
                task=step_data['task'],
                depends_on=step_data.get('depends_on', []),
                condition=step_data.get('condition'),
                lock=step_data.get('lock'),
                priority=step_data.get('priority', 100),
                outputs=step_data.get('outputs', {})
            )
            steps.append(step)
            
        return SopTemplate(name=data['name'], steps=steps)
    
    def list_available_templates(self) -> List[str]:
        """List all available templates.
        
        Returns:
            List[str]: List of available template names
        """
        if not self.templates_dir.exists():
            return []
            
        templates = []
        for file_path in self.templates_dir.glob("*.yaml"):
            templates.append(file_path.stem)
            
        return sorted(templates)
    
    def get_default_template(self) -> SopTemplate:
        """Get the default feature delivery template.
        
        Returns:
            SopTemplate: Default template
        """
        return self.load_template("feature_delivery")

# Global template loader instance
_template_loader: Optional[TemplateLoader] = None

def get_template_loader() -> TemplateLoader:
    """Get the global template loader instance.
    
    Returns:
        TemplateLoader: Global template loader
    """
    global _template_loader
    if _template_loader is None:
        _template_loader = TemplateLoader()
    return _template_loader

def load_template(template_name: str) -> SopTemplate:
    """Convenience function to load a template.
    
    Args:
        template_name: Name of the template to load
        
    Returns:
        SopTemplate: The loaded template
    """
    return get_template_loader().load_template(template_name)

def get_default_template() -> SopTemplate:
    """Convenience function to get the default template.
    
    Returns:
        SopTemplate: Default template
    """
    return get_template_loader().get_default_template()
