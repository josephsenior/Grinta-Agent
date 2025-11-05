"""
Custom LLM Provider Example

This example shows how to add support for a new LLM provider to OpenHands.
"""

from pydantic import SecretStr
from openhands.core.config import LLMConfig
from openhands.core.config.provider_config import ProviderConfig, provider_config_manager
from openhands.llm import LLM


def add_custom_provider():
    """Add a custom LLM provider to the system."""
    
    # Step 1: Create provider configuration
    custom_provider_config = ProviderConfig(
        name='myprovider',
        env_var='MYPROVIDER_API_KEY',
        requires_protocol=True,
        supports_streaming=True,
        required_params={'api_key', 'model'},
        optional_params={'timeout', 'temperature', 'max_tokens'},
        forbidden_params={'custom_llm_provider'},
        api_key_prefixes=['mp-'],  # Your provider's key prefix
        api_key_min_length=20,
        handles_own_routing=False,
        requires_custom_llm_provider=False,
    )
    
    # Step 2: Register provider (in production, add to provider_config.py)
    # For this example, we'll just demonstrate usage
    print(f"Provider config created: {custom_provider_config.name}")
    
    # Step 3: Configure LLM with your provider
    llm_config = LLMConfig(
        model="myprovider/my-model-name",
        api_key=SecretStr("mp-your-api-key-here"),
        base_url="https://api.myprovider.com/v1",  # Your provider's API endpoint
        temperature=0.0,
        max_output_tokens=4000,
    )
    
    # Step 4: Create LLM instance
    llm = LLM(
        config=llm_config,
        service_id="custom-provider-example"
    )
    
    # Step 5: Test the connection
    try:
        print("Testing LLM connection...")
        response = llm.completion(
            messages=[{
                "role": "user",
                "content": "Hello! Please respond with 'Hello, World!'"
            }]
        )
        
        print(f"✅ Success! Response: {response.choices[0].message.content}")
        print(f"Cost: ${llm.metrics.accumulated_cost:.4f}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nCommon issues:")
        print("1. Check API key is correct")
        print("2. Check base_url is reachable")
        print("3. Check model name is correct")
        print("4. Review provider's API documentation")


def add_to_codebase():
    """Instructions for permanently adding the provider."""
    
    print("\n" + "="*60)
    print("To permanently add this provider to OpenHands:")
    print("="*60)
    
    print("""
1. Edit: openhands/core/config/provider_config.py
   
   Add to _load_provider_configurations():
   
   configs['myprovider'] = ProviderConfig(
       name='myprovider',
       env_var='MYPROVIDER_API_KEY',
       requires_protocol=True,
       supports_streaming=True,
       required_params={'api_key', 'model'},
       optional_params={'timeout', 'temperature', 'max_tokens'},
       forbidden_params={'custom_llm_provider'},
       api_key_prefixes=['mp-'],
       api_key_min_length=20,
   )

2. (Optional) Add model feature patterns:
   
   Edit: openhands/llm/model_features.py
   
   If your provider supports function calling:
   FUNCTION_CALLING_PATTERNS = [
       # ... existing patterns
       "myprovider/*",  # All models support function calling
   ]
   
   If your provider supports prompt caching:
   PROMPT_CACHE_PATTERNS = [
       # ... existing patterns  
       "myprovider/cached-model-*",
   ]

3. (Optional) Add to model list:
   
   Edit: openhands/utils/llm.py
   
   Add to get_supported_llm_models():
   model_list.extend([
       "myprovider/model-1",
       "myprovider/model-2",
   ])

4. Test your provider:
   
   # In .env:
   LLM_MODEL=myprovider/model-1
   MYPROVIDER_API_KEY=mp-your-key
   
   # Start OpenHands
   poetry run python -m openhands.server.listen
   
5. Submit PR:
   
   - Include provider config
   - Add tests if possible
   - Update documentation
   - Explain use case (why this provider?)
""")


if __name__ == "__main__":
    print("Custom LLM Provider Example")
    print("="*60)
    
    # Add and test custom provider
    add_custom_provider()
    
    # Show how to add permanently
    add_to_codebase()

