"""Prompt Evolver for Dynamic Prompt Optimization.

Uses LLM to analyze underperforming prompts and generate improved variants
based on performance patterns and error analysis.
"""

from __future__ import annotations

import json
import random
from typing import Dict, List, Optional, Tuple

from .models import PromptCategory, PromptVariant
from .registry import PromptRegistry
from .tracker import PerformanceTracker
from .optimizer import PromptOptimizer


class PromptEvolver:
    """LLM-powered prompt evolution system."""
    
    def __init__(self, llm, registry: PromptRegistry, tracker: PerformanceTracker, 
                 optimizer: PromptOptimizer):
        """Initialize the prompt evolver.
        
        Args:
            llm: LLM instance for generating new prompts
            registry: Prompt registry for managing variants
            tracker: Performance tracker for analysis
            optimizer: Prompt optimizer for A/B testing

        """
        self.llm = llm
        self.registry = registry
        self.tracker = tracker
        self.optimizer = optimizer
        
        # Evolution strategies
        self.strategies = [
            'refinement',      # Improve existing prompt
            'expansion',       # Add more detail/context
            'simplification',  # Simplify complex prompts
            'restructuring',   # Reorganize prompt structure
            'specialization',  # Make more specific to task
            'generalization'   # Make more broadly applicable
        ]
    
    def evolve_prompt(self, prompt_id: str, max_variants: int = 3) -> List[str]:
        """Evolve a prompt by generating new variants.
        
        Args:
            prompt_id: ID of the prompt to evolve
            max_variants: Maximum number of variants to generate
            
        Returns:
            List of new variant IDs

        """
        # Get candidates for evolution
        candidates = self.optimizer.get_candidates_for_evolution(prompt_id)
        if not candidates:
            return []
        
        new_variant_ids = []
        
        for candidate in candidates[:max_variants]:
            # Analyze the candidate
            analysis = self._analyze_prompt_performance(candidate)
            
            # Generate improved variants
            improved_variants = self._generate_improved_variants(candidate, analysis)
            
            # Register new variants
            for variant_content in improved_variants:
                variant_id = self.optimizer.add_variant(
                    prompt_id=prompt_id,
                    content=variant_content,
                    category=candidate.category,
                    parent_id=candidate.id,
                    metadata={
                        'evolution_strategy': analysis.get('recommended_strategy', 'refinement'),
                        'parent_variant': candidate.id,
                        'generated_at': 'evolver'
                    }
                )
                new_variant_ids.append(variant_id)
        
        return new_variant_ids
    
    def _analyze_prompt_performance(self, variant: PromptVariant) -> Dict[str, any]:
        """Analyze the performance of a prompt variant."""
        metrics = self.tracker.get_variant_metrics(variant.id)
        if not metrics:
            return {'recommended_strategy': 'refinement'}
        
        # Get recent performance data
        recent_performances = [
            p for p in self.tracker._performance_data
            if p.variant_id == variant.id
        ][-10:]  # Last 10 executions
        
        # Analyze error patterns
        error_patterns = self._analyze_error_patterns(recent_performances)
        
        # Determine recommended strategy
        strategy = self._recommend_strategy(metrics, error_patterns)
        
        return {
            'metrics': metrics.to_dict(),
            'error_patterns': error_patterns,
            'recommended_strategy': strategy,
            'sample_size': len(recent_performances)
        }
    
    def _categorize_error(self, error_msg_lower: str) -> str:
        """Categorize an error based on message.
        
        Args:
            error_msg_lower: Lowercase error message
            
        Returns:
            Error category

        """
        if 'timeout' in error_msg_lower:
            return 'timeout'
        elif 'parse' in error_msg_lower or 'json' in error_msg_lower:
            return 'parsing_error'
        elif 'valid' in error_msg_lower or 'invalid' in error_msg_lower:
            return 'validation_error'
        elif 'execution' in error_msg_lower or 'runtime' in error_msg_lower:
            return 'execution_error'
        else:
            return 'other'

    def _categorize_errors(self, failed_performances: List) -> tuple[dict, list]:
        """Categorize all errors and extract common issues.
        
        Args:
            failed_performances: List of failed performances
            
        Returns:
            Tuple of (error_categories, common_issues)

        """
        error_categories = {
            'timeout': 0,
            'parsing_error': 0,
            'validation_error': 0,
            'execution_error': 0,
            'other': 0
        }
        common_issues = []
        
        for perf in failed_performances:
            error_msg = perf.error_message or ''
            
            # Categorize error
            category = self._categorize_error(error_msg.lower())
            error_categories[category] += 1
            
            # Extract issue
            if error_msg:
                common_issues.append(error_msg[:100])
        
        return error_categories, common_issues

    def _analyze_error_patterns(self, performances: List) -> Dict[str, any]:
        """Analyze error patterns from performance data."""
        failed_performances = [p for p in performances if not p.success]
        
        if not failed_performances:
            return {'error_type': 'none', 'common_issues': []}
        
        error_categories, common_issues = self._categorize_errors(failed_performances)
        most_common_error = max(error_categories.items(), key=lambda x: x[1])
        
        return {
            'error_type': most_common_error[0],
            'error_counts': error_categories,
            'common_issues': common_issues[:5],
            'failure_rate': len(failed_performances) / len(performances)
        }
    
    def _recommend_strategy(self, metrics, error_patterns: Dict) -> str:
        """Recommend an evolution strategy based on analysis."""
        # Low success rate -> refinement or expansion
        if metrics.success_rate < 0.5:
            if error_patterns['error_type'] == 'parsing_error':
                return 'simplification'
            elif error_patterns['error_type'] == 'validation_error':
                return 'specialization'
            else:
                return 'refinement'
        
        # High execution time -> simplification
        if metrics.avg_execution_time > 30:  # 30 seconds
            return 'simplification'
        
        # High error rate -> refinement
        if metrics.error_rate > 0.3:
            return 'refinement'
        
        # Low composite score -> expansion or restructuring
        if metrics.composite_score < 0.6:
            return 'expansion'
        
        # Default to refinement
        return 'refinement'
    
    def _generate_improved_variants(self, variant: PromptVariant, 
                                  analysis: Dict) -> List[str]:
        """Generate improved variants using LLM."""
        strategy = analysis['recommended_strategy']
        error_patterns = analysis['error_patterns']
        metrics = analysis['metrics']
        
        # Create evolution prompt
        evolution_prompt = self._create_evolution_prompt(
            original_prompt=variant.content,
            strategy=strategy,
            error_patterns=error_patterns,
            metrics=metrics,
            category=variant.category
        )
        
        try:
            # Generate variants using LLM
            response = self.llm.generate(
                prompt=evolution_prompt,
                max_tokens=2000,
                temperature=0.7
            )
            
            # Parse response
            variants = self._parse_evolution_response(response, strategy)
            
            return variants
            
        except Exception as e:
            print(f"Error generating evolved variants: {e}")
            # Fallback to simple strategies
            return self._fallback_evolution(variant, strategy)
    
    def _create_evolution_prompt(self, original_prompt: str, strategy: str,
                               error_patterns: Dict, metrics: Dict, 
                               category: PromptCategory) -> str:
        """Create a prompt for LLM-based evolution."""
        strategy_instructions = {
            'refinement': """
Refine the existing prompt to improve clarity and effectiveness. Focus on:
- Making instructions clearer and more specific
- Fixing any ambiguous language
- Improving the logical flow
- Addressing common failure points
""",
            'expansion': """
Expand the prompt with additional context and guidance. Add:
- More detailed instructions
- Examples or templates
- Edge case handling
- Additional context that might help
""",
            'simplification': """
Simplify the prompt to make it more concise and easier to follow. Focus on:
- Removing unnecessary complexity
- Using simpler language
- Breaking down complex instructions
- Making the core task clearer
""",
            'restructuring': """
Restructure the prompt to improve organization and flow. Consider:
- Reordering sections for better logic
- Using clearer formatting
- Grouping related instructions
- Improving the overall structure
""",
            'specialization': """
Make the prompt more specific to its intended use case. Focus on:
- Adding domain-specific context
- Including relevant constraints
- Making instructions more targeted
- Addressing specific requirements
""",
            'generalization': """
Make the prompt more broadly applicable while maintaining effectiveness. Focus on:
- Removing overly specific constraints
- Making instructions more flexible
- Adding adaptability
- Broadening applicability
"""
        }
        
        error_context = ""
        if error_patterns['error_type'] != 'none':
            error_context = f"""
Common Error Patterns:
- Error Type: {error_patterns['error_type']}
- Failure Rate: {error_patterns['failure_rate']:.2%}
- Common Issues: {', '.join(error_patterns['common_issues'][:3])}
"""
        
        metrics_context = f"""
Current Performance:
- Success Rate: {metrics['success_rate']:.2%}
- Average Execution Time: {metrics['avg_execution_time']:.2f}s
- Error Rate: {metrics['error_rate']:.2%}
- Composite Score: {metrics['composite_score']:.2f}
"""
        
        return f"""
You are an expert prompt engineer. Your task is to improve the following prompt using the {strategy} strategy.

{strategy_instructions.get(strategy, strategy_instructions['refinement'])}

Original Prompt:
{original_prompt}

{error_context}

{metrics_context}

Category: {category.value}

Please generate 2-3 improved variants of this prompt. Each variant should:
1. Address the identified issues
2. Follow the {strategy} strategy
3. Maintain the core functionality
4. Be clearly formatted and easy to understand

Return your response as a JSON array of strings, where each string is an improved prompt variant:

[
  "Improved prompt variant 1...",
  "Improved prompt variant 2...",
  "Improved prompt variant 3..."
]
"""
    
    def _try_parse_json_array(self, response: str) -> Optional[List[str]]:
        """Try to parse response as JSON array.
        
        Args:
            response: Response string to parse
            
        Returns:
            List of variants or None if parsing fails

        """
        try:
            start_idx = response.find('[')
            end_idx = response.rfind(']')
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx + 1]
                variants = json.loads(json_str)
                
                if isinstance(variants, list):
                    return [str(v) for v in variants if isinstance(v, str)]
        except Exception:
            pass
        
        return None

    def _parse_text_variants(self, response: str) -> List[str]:
        """Parse variants from text response.
        
        Args:
            response: Text response to parse
            
        Returns:
            List of extracted variants

        """
        lines = response.split('\n')
        variants = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('//'):
                continue
            
            # Remove common prefixes
            for prefix in ['- ', '* ', '1. ', '2. ', '3. ']:
                if line.startswith(prefix):
                    line = line[len(prefix):]
                    break
            
            if len(line) > 20:  # Reasonable minimum length
                variants.append(line)
        
        return variants[:3]

    def _parse_evolution_response(self, response: str, strategy: str) -> List[str]:
        """Parse the LLM response to extract prompt variants."""
        try:
            # Try JSON parsing first
            if json_variants := self._try_parse_json_array(response):
                return json_variants
            
            # Fallback to text parsing
            return self._parse_text_variants(response)
            
        except Exception as e:
            print(f"Error parsing evolution response: {e}")
            return []
    
    def _fallback_evolution(self, variant: PromptVariant, strategy: str) -> List[str]:
        """Fallback evolution strategies when LLM fails."""
        original = variant.content
        
        if strategy == 'simplification':
            # Simple simplification: remove extra whitespace, shorten sentences
            simplified = ' '.join(original.split())
            return [simplified]
        
        elif strategy == 'expansion':
            # Add common improvements
            expanded = f"{original}\n\nAdditional Guidelines:\n- Be thorough and methodical\n- Double-check your work\n- Ask for clarification if needed"
            return [expanded]
        
        elif strategy == 'refinement':
            # Basic refinement: improve formatting
            refined = original.replace('  ', ' ').replace('\n\n\n', '\n\n')
            return [refined]
        
        else:
            # Default: return original with minor improvements
            improved = f"IMPROVED: {original}"
            return [improved]
    
    def evolve_all_underperforming(self, min_score: float = 0.7) -> Dict[str, List[str]]:
        """Evolve all prompts with performance below threshold."""
        results = {}
        
        # Get all prompt IDs
        prompt_ids = self.registry.get_prompt_ids()
        
        for prompt_id in prompt_ids:
            # Check if prompt needs evolution
            if self.optimizer.should_evolve_prompt(prompt_id):
                new_variants = self.evolve_prompt(prompt_id)
                if new_variants:
                    results[prompt_id] = new_variants
        
        return results
    
    def get_evolution_history(self, prompt_id: str) -> List[Dict[str, any]]:
        """Get evolution history for a prompt."""
        variants = self.registry.get_variants_for_prompt(prompt_id)
        
        # Filter variants that were generated by evolution
        evolved_variants = [
            v for v in variants 
            if v.metadata.get('generated_at') == 'evolver'
        ]
        
        # Sort by creation time
        evolved_variants.sort(key=lambda v: v.created_at)
        
        history = []
        for variant in evolved_variants:
            metrics = self.tracker.get_variant_metrics(variant.id)
            history.append({
                'variant_id': variant.id,
                'content': variant.content,
                'strategy': variant.metadata.get('evolution_strategy', 'unknown'),
                'parent_id': variant.parent_id,
                'created_at': variant.created_at.isoformat(),
                'metrics': metrics.to_dict() if metrics else None
            })
        
        return history
    
    def _count_strategies(self, evolved_variants: List) -> dict:
        """Count variants by evolution strategy.
        
        Args:
            evolved_variants: List of evolved variants
            
        Returns:
            Dictionary of strategy counts

        """
        strategy_counts = {}
        for variant in evolved_variants:
            strategy = variant.metadata.get('evolution_strategy', 'unknown')
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        return strategy_counts

    def _calculate_strategy_success_rate(self, strategy: str, evolved_variants: list) -> float:
        """Calculate success rate for a specific strategy.
        
        Args:
            strategy: Strategy name
            evolved_variants: List of evolved variants
            
        Returns:
            Success rate (0.0 to 1.0)

        """
        strategy_variants = [
            v for v in evolved_variants 
            if v.metadata.get('evolution_strategy') == strategy
        ]
        
        if not strategy_variants:
            return 0.0
        
        total_executions = sum(v.total_executions for v in strategy_variants)
        successful_executions = sum(v.successful_executions for v in strategy_variants)
        return successful_executions / total_executions if total_executions > 0 else 0.0

    def _calculate_strategy_success_rates(self, strategy_counts: dict, evolved_variants: list) -> dict:
        """Calculate success rates for all strategies.
        
        Args:
            strategy_counts: Dictionary of strategy counts
            evolved_variants: List of evolved variants
            
        Returns:
            Dictionary of strategy success rates

        """
        return {
            strategy: self._calculate_strategy_success_rate(strategy, evolved_variants)
            for strategy in strategy_counts
        }

    def get_evolution_statistics(self) -> Dict[str, any]:
        """Get statistics about evolution activities."""
        all_variants = list(self.registry._variants.values())
        
        evolved_variants = [
            v for v in all_variants 
            if v.metadata.get('generated_at') == 'evolver'
        ]
        
        strategy_counts = self._count_strategies(evolved_variants)
        strategy_success_rates = self._calculate_strategy_success_rates(strategy_counts, evolved_variants)
        
        return {
            'total_evolved_variants': len(evolved_variants),
            'strategy_counts': strategy_counts,
            'strategy_success_rates': strategy_success_rates,
            'evolution_rate': len(evolved_variants) / len(all_variants) if all_variants else 0
        }
