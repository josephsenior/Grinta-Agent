import Joi from 'joi';

/**
 * Validation schemas for different request types
 */
export const validationSchemas = {
  // Component-related schemas
  componentName: Joi.object({
    componentName: Joi.string()
      .required()
      .min(1)
      .max(100)
      .description('Name of the shadcn/ui component'),
  }),

  // Search schemas
  searchQuery: Joi.object({
    query: Joi.string().required().min(1).max(500).description('Search query string'),
  }),

  // Optional query schemas
  optionalQuery: Joi.object({
    query: Joi.string().optional().max(500).description('Optional query string'),
  }),

  // Block schemas
  blockQuery: Joi.object({
    query: Joi.string().optional().max(500).description('Optional search query'),
    category: Joi.string().optional().max(100).description('Optional category filter'),
  }),

  // Directory structure schemas
  directoryStructure: Joi.object({
    path: Joi.string().optional().max(500).description('Path within the repository'),
    owner: Joi.string().optional().max(100).description('Repository owner'),
    repo: Joi.string().optional().max(100).description('Repository name'),
    branch: Joi.string().optional().max(100).description('Branch name'),
  }),

  // Block schemas
  blockRequest: Joi.object({
    blockName: Joi.string().required().min(1).max(200).description('Name of the block'),
    includeComponents: Joi.boolean().optional().description('Whether to include component files'),
  }),

  // Resource schemas
  resourceRequest: Joi.object({
    uri: Joi.string().required().min(1).max(1000).description('Resource URI'),
  }),

  // Prompt schemas
  promptRequest: Joi.object({
    name: Joi.string().required().min(1).max(200).description('Prompt name'),
    arguments: Joi.object().optional().description('Prompt arguments'),
  }),

  // Tool schemas
  toolRequest: Joi.object({
    name: Joi.string().required().min(1).max(200).description('Tool name'),
    arguments: Joi.object().optional().description('Tool arguments'),
  }),
};

/**
 * Validate request parameters against a schema
 * @param schema Joi schema to validate against
 * @param params Parameters to validate
 * @returns Validated parameters
 * @throws ValidationError if validation fails
 */
export function validateRequest<T>(schema: Joi.ObjectSchema, params: any): T {
  try {
    const { error, value } = schema.validate(params, {
      abortEarly: false,
      stripUnknown: true,
      allowUnknown: false,
    });

    if (error) {
      const errorMessages = error.details
        .map((detail) => `${detail.path.join('.')}: ${detail.message}`)
        .join(', ');

      throw new Error(`Validation failed: ${errorMessages}`);
    }

    return value as T;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error(
      `Unexpected validation error: ${error instanceof Error ? error.message : String(error)}`
    );
  }
}

/**
 * Get validation schema for a specific method
 * @param method Method name
 * @returns Joi schema or undefined
 */
export function getValidationSchema(method: string): Joi.ObjectSchema | undefined {
  const schemaMap: Record<string, Joi.ObjectSchema> = {
    // Component methods
    get_component: validationSchemas.componentName,
    get_component_demo: validationSchemas.componentName,
    get_component_metadata: validationSchemas.componentName,
    get_component_details: validationSchemas.componentName,
    get_examples: validationSchemas.componentName,
    get_usage: validationSchemas.componentName,

    // Search methods
    search_components: validationSchemas.searchQuery,
    get_themes: validationSchemas.optionalQuery,
    get_blocks: validationSchemas.blockQuery,

    // Directory methods
    get_directory_structure: validationSchemas.directoryStructure,

    // Block methods
    get_block: validationSchemas.blockRequest,

    // Resource methods
    read_resource: validationSchemas.resourceRequest,

    // Prompt methods
    get_prompt: validationSchemas.promptRequest,

    // Tool methods
    call_tool: validationSchemas.toolRequest,
  };

  return schemaMap[method];
}

/**
 * Validate and sanitize input parameters
 * @param method Method name
 * @param params Parameters to validate
 * @returns Validated and sanitized parameters
 */
export function validateAndSanitizeParams<T>(method: string, params: any): T {
  const schema = getValidationSchema(method);

  if (!schema) {
    // If no specific schema found, return params as-is
    return params as T;
  }

  return validateRequest<T>(schema, params);
}
