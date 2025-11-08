//.CommonJS
var CSSOM = {};
///CommonJS


/**
 * Parses a CSS string and returns a CSSOM.CSSStyleSheet object representing the parsed stylesheet.
 *
 * @param {string} token - The CSS string to parse.
 * @param {object} [opts] - Optional parsing options.
 * @param {object} [opts.globalObject] - An optional global object to attach to the stylesheet. Useful on jsdom webplatform tests.
 * @param {function|boolean} [errorHandler] - Optional error handler function or `true` to use `console.error`.
 * @returns {CSSOM.CSSStyleSheet} The parsed CSSStyleSheet object.
 */
CSSOM.parse = function parse(token, opts, errorHandler) {
	errorHandler = errorHandler === true ? (console && console.error) : errorHandler;

	var i = 0;

	/**
		"before-selector" or
		"selector" or
		"atRule" or
		"atBlock" or
		"conditionBlock" or
		"before-name" or
		"name" or
		"before-value" or
		"value"
	*/
	var state = "before-selector";

	var index;
	var buffer = "";
	var valueParenthesisDepth = 0;

	var SIGNIFICANT_WHITESPACE = {
		"name": true,
		"before-name": true,
		"selector": true,
		"value": true,
		"value-parenthesis": true,
		"atRule": true,
		"importRule-begin": true,
		"importRule": true,
		"namespaceRule-begin": true,
		"namespaceRule": true,
		"atBlock": true,
		"containerBlock": true,
		"conditionBlock": true,
		"counterStyleBlock": true,
		'documentRule-begin': true,
		"layerBlock": true
	};

	var styleSheet = new CSSOM.CSSStyleSheet();

	if (opts && opts.globalObject) {
		styleSheet.__globalObject = opts.globalObject;
	}

	// @type CSSStyleSheet|CSSMediaRule|CSSContainerRule|CSSSupportsRule|CSSFontFaceRule|CSSKeyframesRule|CSSDocumentRule
	var currentScope = styleSheet;

	// @type CSSMediaRule|CSSContainerRule|CSSSupportsRule|CSSKeyframesRule|CSSDocumentRule
	var parentRule;

	var ancestorRules = [];
	var prevScope;

	var name, priority="", styleRule, mediaRule, containerRule, counterStyleRule, supportsRule, importRule, fontFaceRule, keyframesRule, documentRule, hostRule, startingStyleRule, layerBlockRule, layerStatementRule, nestedSelectorRule, namespaceRule;

	// Track defined namespace prefixes for validation
	var definedNamespacePrefixes = {};

	var atKeyframesRegExp = /@(-(?:\w+-)+)?keyframes/g; // Match @keyframes and vendor-prefixed @keyframes
	// Regex above is not ES5 compliant
	// var atRulesStatemenRegExp = /(?<!{.*)[;}]\s*/; // Match a statement by verifying it finds a semicolon or closing brace not followed by another semicolon or closing brace
	var beforeRulePortionRegExp = /{(?!.*{)|}(?!.*})|;(?!.*;)|\*\/(?!.*\*\/)/g; // Match the closest allowed character (a opening or closing brace, a semicolon or a comment ending) before the rule
	var beforeRuleValidationRegExp = /^[\s{};]*(\*\/\s*)?$/; // Match that the portion before the rule is empty or contains only whitespace, semicolons, opening/closing braces, and optionally a comment ending (*/) followed by whitespace
	var forwardRuleValidationRegExp = /(?:\(|\s|\/\*)/; // Match that the rule is followed by any whitespace, a opening comment or a condition opening parenthesis
	var forwardImportRuleValidationRegExp = /(?:\s|\/\*|'|")/; // Match that the rule is followed by any whitespace, an opening comment, a single quote or double quote
	var forwardRuleClosingBraceRegExp = /{[^{}]*}|}/; // Finds the next closing brace of a rule block
	var forwardRuleSemicolonAndOpeningBraceRegExp = /^.*?({|;)/; // Finds the next semicolon or opening brace after the at-rule	
	var layerRuleNameRegExp = /^(-?[_a-zA-Z]+(\.[_a-zA-Z]+)*[_a-zA-Z0-9-]*)$/; // Validates a single @layer name

	/**
	 * Searches for the first occurrence of a CSS at-rule statement terminator (`;` or `}`) 
	 * that is not inside a brace block within the given string. Mimics the behavior of a 
	 * regular expression match for such terminators, including any trailing whitespace.
	 * @param {string} str - The string to search for at-rule statement terminators.
	 * @returns {object | null} {0: string, index: number} or null if no match is found.
	 */
	function atRulesStatemenRegExpES5Alternative(ruleSlice) {
		for (var i = 0; i < ruleSlice.length; i++) {
			var char = ruleSlice[i];

			if (char === ';' || char === '}') {
				// Simulate negative lookbehind: check if there is a { before this position
				var sliceBefore = ruleSlice.substring(0, i);
				var openBraceIndex = sliceBefore.indexOf('{');

				if (openBraceIndex === -1) {
					// No { found before, so we treat it as a valid match
					var match = char;
					var j = i + 1;

					while (j < ruleSlice.length && /\s/.test(ruleSlice[j])) {
						match += ruleSlice[j];
						j++;
					}

					var matchObj = [match];
					matchObj.index = i;
					matchObj.input = ruleSlice;
					return matchObj;
				}
			}
		}

		return null;
	}

	/**
	 * Finds the first balanced block (including nested braces) in the string, starting from fromIndex.
	 * Returns an object similar to RegExp.prototype.match output.
	 * @param {string} str - The string to search.
	 * @param {number} [fromIndex=0] - The index to start searching from.
	 * @returns {object|null} - { 0: matchedString, index: startIndex, input: str } or null if not found.
	 */
	function matchBalancedBlock(str, fromIndex) {
		fromIndex = fromIndex || 0;
		var openIndex = str.indexOf('{', fromIndex);
		if (openIndex === -1) return null;
		var depth = 0;
		for (var i = openIndex; i < str.length; i++) {
			if (str[i] === '{') {
				depth++;
			} else if (str[i] === '}') {
				depth--;
				if (depth === 0) {
					var matchedString = str.slice(openIndex, i + 1);
					return {
						0: matchedString,
						index: openIndex,
						input: str
					};
				}
			}
		}
		return null;
	}

	/**
	 * Advances the index `i` to skip over a balanced block of curly braces in the given string.
	 * This is typically used to ignore the contents of a CSS rule block.
	 *
	 * @param {number} i - The current index in the string to start searching from.
	 * @param {string} str - The string containing the CSS code.
	 * @param {number} fromIndex - The index in the string where the balanced block search should begin.
	 * @returns {number} The updated index after skipping the balanced block.
	 */
	function ignoreBalancedBlock(i, str, fromIndex) {
		var ruleClosingMatch = matchBalancedBlock(str, fromIndex);
		if (ruleClosingMatch) {
			var ignoreRange = ruleClosingMatch.index + ruleClosingMatch[0].length;
			i+= ignoreRange;
			if (token.charAt(i) === '}') {
				i -= 1;
			}
		} else {
			i += str.length;
		}
		return i;	
	}

	var parseError = function(message) {
		var lines = token.substring(0, i).split('\n');
		var lineCount = lines.length;
		var charCount = lines.pop().length + 1;
		var error = new Error(message + ' (line ' + lineCount + ', char ' + charCount + ')');
		error.line = lineCount;
		/* jshint sub : true */
		error['char'] = charCount;
		error.styleSheet = styleSheet;
		// Print the error but continue parsing the sheet
		try {
			throw error;
		} catch(e) {
			errorHandler && errorHandler(e);
		}
	};

	var validateAtRule = function(atRuleKey, validCallback, cannotBeNested) {
		var isValid = false;
		var sourceRuleRegExp = atRuleKey === "@import" ? forwardImportRuleValidationRegExp : forwardRuleValidationRegExp;
		var ruleRegExp = new RegExp(atRuleKey + sourceRuleRegExp.source, sourceRuleRegExp.flags);
		var ruleSlice = token.slice(i);
		// Not all rules can be nested, if the rule cannot be nested and is in the root scope, do not perform the check
		var shouldPerformCheck = cannotBeNested && currentScope !== styleSheet ? false : true;
		// First, check if there is no invalid characters just after the at-rule
		if (shouldPerformCheck && ruleSlice.search(ruleRegExp) === 0) {
			// Find the closest allowed character before the at-rule (a opening or closing brace, a semicolon or a comment ending)
			var beforeSlice = token.slice(0, i);
			var regexBefore = new RegExp(beforeRulePortionRegExp.source, beforeRulePortionRegExp.flags);
			var matches = beforeSlice.match(regexBefore);
			var lastI = matches ? beforeSlice.lastIndexOf(matches[matches.length - 1]) : 0;
			var toCheckSlice = token.slice(lastI, i);
			// Check if we don't have any invalid in the portion before the `at-rule` and the closest allowed character
			var checkedSlice = toCheckSlice.search(beforeRuleValidationRegExp);
			if (checkedSlice === 0) {
				isValid = true;
			}
		}
		if (!isValid) {
			// If it's invalid the browser will simply ignore the entire invalid block
			// Use regex to find the closing brace of the invalid rule
			
			// Regex used above is not ES5 compliant. Using alternative.
			// var ruleStatementMatch = ruleSlice.match(atRulesStatemenRegExp); //
			var ruleStatementMatch = atRulesStatemenRegExpES5Alternative(ruleSlice);

			// If it's a statement inside a nested rule, ignore only the statement
			if (ruleStatementMatch && currentScope !== styleSheet) {
				var ignoreEnd = ruleStatementMatch[0].indexOf(";");
				i += ruleStatementMatch.index + ignoreEnd;
				return;
			}

			// Check if there's a semicolon before the invalid at-rule and the first opening brace
			if (atRuleKey === "@layer") {
				var ruleSemicolonAndOpeningBraceMatch = ruleSlice.match(forwardRuleSemicolonAndOpeningBraceRegExp);
				if (ruleSemicolonAndOpeningBraceMatch && ruleSemicolonAndOpeningBraceMatch[1] === ";" ) {
					// Ignore the rule block until the semicolon
					i += ruleSemicolonAndOpeningBraceMatch.index + ruleSemicolonAndOpeningBraceMatch[0].length;
					state = "before-selector";
					return;
				}
			}

			// Ignore the entire rule block (if it's a statement it should ignore the statement plus the next block)
			i = ignoreBalancedBlock(i, ruleSlice);
			state = "before-selector";
		} else {
			validCallback.call(this);
		}
	}

	/**
	 * Validates a basic CSS selector, allowing for deeply nested balanced parentheses in pseudo-classes.
	 * This function replaces the previous basicSelectorRegExp.
	 * 
	 * This function matches:
	 * - Type selectors (e.g., `div`, `span`)
	 * - Universal selector (`*`)
	 * - Namespace selectors (e.g., `*|div`, `custom|div`, `|div`)
	 * - ID selectors (e.g., `#header`, `#a\ b`, `#åèiöú`)
	 * - Class selectors (e.g., `.container`, `.a\ b`, `.åèiöú`)
	 * - Attribute selectors (e.g., `[type="text"]`)
	 * - Pseudo-classes and pseudo-elements (e.g., `:hover`, `::before`, `:nth-child(2)`)
	 * - Pseudo-classes with nested parentheses, including cases where parentheses are nested inside arguments,
	 *   such as `:has(.sel:nth-child(3n))`
	 * - The parent selector (`&`)
	 * - Combinators (`>`, `+`, `~`) with optional whitespace
	 * - Whitespace (descendant combinator)
	 *
	 * Unicode and escape sequences are allowed in identifiers.
	 *
	 * @param {string} selector
	 * @returns {boolean}
	 */
	function basicSelectorValidator(selector) {
		var length = selector.length;
		var i = 0;
		var stack = [];
		var inAttr = false;
		var inSingleQuote = false;
		var inDoubleQuote = false;

		while (i < length) {
			var char = selector[i];

			if (inSingleQuote) {
				if (char === "'" && selector[i - 1] !== "\\") {
					inSingleQuote = false;
				}
			} else if (inDoubleQuote) {
				if (char === '"' && selector[i - 1] !== "\\") {
					inDoubleQuote = false;
				}
			} else if (inAttr) {
				if (char === "]") {
					inAttr = false;
				} else if (char === "'") {
					inSingleQuote = true;
				} else if (char === '"') {
					inDoubleQuote = true;
				}
			} else {
				if (char === "[") {
					inAttr = true;
				} else if (char === "'") {
					inSingleQuote = true;
				} else if (char === '"') {
					inDoubleQuote = true;
				} else if (char === "(") {
					stack.push("(");
				} else if (char === ")") {
					if (!stack.length || stack.pop() !== "(") {
						return false;
					}
				}
			}
			i++;
		}

		// If any stack or quote/attr context remains, it's invalid
		if (stack.length || inAttr || inSingleQuote || inDoubleQuote) {
			return false;
		}

		// Fallback to a loose regexp for the overall selector structure (without deep paren matching)
		// This is similar to the original, but without nested paren limitations
		// Modified to support namespace selectors: *|element, prefix|element, |element
		// Fixed attribute selector regex to properly handle |=, ~=, ^=, $=, *= operators
		var looseSelectorRegExp = /^((?:(?:\*|[a-zA-Z_\u00A0-\uFFFF\\][a-zA-Z0-9_\u00A0-\uFFFF\-\\]*|)\|)?[a-zA-Z_\u00A0-\uFFFF\\][a-zA-Z0-9_\u00A0-\uFFFF\-\\]*|(?:(?:\*|[a-zA-Z_\u00A0-\uFFFF\\][a-zA-Z0-9_\u00A0-\uFFFF\-\\]*|)\|)?\*|#[a-zA-Z0-9_\u00A0-\uFFFF\-\\]+|\.[a-zA-Z0-9_\u00A0-\uFFFF\-\\]+|\[(?:[^\[\]'"]|'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")*(?:\s+[iI])?\]|::?[a-zA-Z0-9_\u00A0-\uFFFF\-\\]+(?:\((.*)\))?|&|\s*[>+~]\s*|\s+)+$/;
		return looseSelectorRegExp.test(selector);
	}

	/**
	 * Regular expression to match CSS pseudo-classes with arguments.
	 *
	 * Matches patterns like `:pseudo-class(argument)`, capturing the pseudo-class name and its argument.
	 *
	 * Capture groups:
	 *   1. The pseudo-class name (letters and hyphens).
	 *   2. The argument inside the parentheses (can contain nested parentheses, quoted strings, and other characters.).
	 *
	 * Global flag (`g`) is used to find all matches in the input string.
	 *
	 * Example matches:
	 *   - :nth-child(2n+1)
	 *   - :has(.sel:nth-child(3n))
	 *   - :not(".foo, .bar")
	 * @type {RegExp}
	 */
	var globalPseudoClassRegExp = /:([a-zA-Z-]+)\(((?:[^()"]+|"[^"]*"|'[^']*'|\((?:[^()"]+|"[^"]*"|'[^']*')*\))*?)\)/g;

	/**
	 * Parses a CSS selector string and splits it into parts, handling nested parentheses.
	 *
	 * This function is useful for splitting selectors that may contain nested function-like
	 * syntax (e.g., :not(.foo, .bar)), ensuring that commas inside parentheses do not split
	 * the selector.
	 *
	 * @param {string} selector - The CSS selector string to parse.
	 * @returns {string[]} An array of selector parts, split by top-level commas, with whitespace trimmed.
	 */
	function parseAndSplitNestedSelectors(selector) {
		var depth = 0;
		var buffer = "";
		var parts = [];
		var inSingleQuote = false;
		var inDoubleQuote = false;
		var i, char;

		for (i = 0; i < selector.length; i++) {
			char = selector.charAt(i);

			if (char === "'" && !inDoubleQuote) {
				inSingleQuote = !inSingleQuote;
				buffer += char;
			} else if (char === '"' && !inSingleQuote) {
				inDoubleQuote = !inDoubleQuote;
				buffer += char;
			} else if (!inSingleQuote && !inDoubleQuote) {
				if (char === '(') {
					depth++;
					buffer += char;
				} else if (char === ')') {
					depth--;
					buffer += char;
					if (depth === 0) {
						parts.push(buffer.replace(/^\s+|\s+$/g, ""));
						buffer = "";
					}
				} else if (char === ',' && depth === 0) {
					if (buffer.replace(/^\s+|\s+$/g, "")) {
						parts.push(buffer.replace(/^\s+|\s+$/g, ""));
					}
					buffer = "";
				} else {
					buffer += char;
				}
			} else {
				buffer += char;
			}
		}

		if (buffer.replace(/^\s+|\s+$/g, "")) {
			parts.push(buffer.replace(/^\s+|\s+$/g, ""));
		}

		return parts;
	}

	/**
	 * Validates a CSS selector string, including handling of nested selectors within certain pseudo-classes.
	 *
	 * This function checks if the provided selector is valid according to the rules defined by
	 * `basicSelectorValidator`. For pseudo-classes that accept selector lists (such as :not, :is, :has, :where),
	 * it recursively validates each nested selector using the same validation logic.
	 *
	 * @param {string} selector - The CSS selector string to validate.
	 * @returns {boolean} Returns `true` if the selector is valid, otherwise `false`.
	 */

	// Cache to store validated selectors
	var validatedSelectorsCache = new Map();

	// Only pseudo-classes that accept selector lists should recurse
	var selectorListPseudoClasses = {
		'not': true,
		'is': true,
		'has': true,
		'where': true
	};

	function validateSelector(selector) {
		if (validatedSelectorsCache.has(selector)) {
			return validatedSelectorsCache.get(selector);
		}

		// Use a non-global regex to find all pseudo-classes with arguments
		var pseudoClassMatches = [];
		var pseudoClassRegExp = new RegExp(globalPseudoClassRegExp.source, globalPseudoClassRegExp.flags);
		var match;
		while ((match = pseudoClassRegExp.exec(selector)) !== null) {
			pseudoClassMatches.push(match);
		}

		for (var j = 0; j < pseudoClassMatches.length; j++) {
			var pseudoClass = pseudoClassMatches[j][1];
			if (selectorListPseudoClasses.hasOwnProperty(pseudoClass)) {
				var nestedSelectors = parseAndSplitNestedSelectors(pseudoClassMatches[j][2]);
				for (var i = 0; i < nestedSelectors.length; i++) {
					var nestedSelector = nestedSelectors[i];
					if (!validatedSelectorsCache.has(nestedSelector)) {
						var nestedSelectorValidation = validateSelector(nestedSelector);
						validatedSelectorsCache.set(nestedSelector, nestedSelectorValidation);
						if (!nestedSelectorValidation) {
							validatedSelectorsCache.set(selector, false);
							return false;
						}
					} else if (!validatedSelectorsCache.get(nestedSelector)) {
						validatedSelectorsCache.set(selector, false);
						return false;
					}
				}
			}
		}

		var basicSelectorValidation = basicSelectorValidator(selector);
		validatedSelectorsCache.set(selector, basicSelectorValidation);

		return basicSelectorValidation;
	}

	/**
	 * Validates namespace selectors by checking if the namespace prefix is defined.
	 * 
	 * @param {string} selector - The CSS selector to validate
	 * @returns {boolean} Returns true if the namespace is valid, false otherwise
	 */
	function validateNamespaceSelector(selector) {
		// Check if selector contains a namespace prefix
		// We need to ignore pipes inside attribute selectors
		var pipeIndex = -1;
		var inAttr = false;
		var inSingleQuote = false;
		var inDoubleQuote = false;
		
		for (var i = 0; i < selector.length; i++) {
			var char = selector[i];
			
			if (inSingleQuote) {
				if (char === "'" && selector[i - 1] !== "\\") {
					inSingleQuote = false;
				}
			} else if (inDoubleQuote) {
				if (char === '"' && selector[i - 1] !== "\\") {
					inDoubleQuote = false;
				}
			} else if (inAttr) {
				if (char === "]") {
					inAttr = false;
				} else if (char === "'") {
					inSingleQuote = true;
				} else if (char === '"') {
					inDoubleQuote = true;
				}
			} else {
				if (char === "[") {
					inAttr = true;
				} else if (char === "|" && !inAttr) {
					// This is a namespace separator, not an attribute operator
					pipeIndex = i;
					break;
				}
			}
		}
		
		if (pipeIndex === -1) {
			return true; // No namespace, always valid
		}
		
		var namespacePrefix = selector.substring(0, pipeIndex);
		
		// Universal namespace (*|) and default namespace (|) are always valid
		if (namespacePrefix === '*' || namespacePrefix === '') {
			return true;
		}
		
		// Check if the custom namespace prefix is defined
		return definedNamespacePrefixes.hasOwnProperty(namespacePrefix);
	}

	/**
	 * Checks if a given CSS selector text is valid by splitting it by commas
	 * and validating each individual selector using the `validateSelector` function.
	 *
	 * @param {string} selectorText - The CSS selector text to validate. Can contain multiple selectors separated by commas.
	 * @returns {boolean} Returns true if all selectors are valid, otherwise false.
	 */
	function isValidSelectorText(selectorText) {
		// Check for newlines inside single or double quotes using regex
		// This matches any quoted string (single or double) containing a newline
		var quotedNewlineRegExp = /(['"])(?:\\.|[^\\])*?\1/g;
		var match;
		while ((match = quotedNewlineRegExp.exec(selectorText)) !== null) {
			if (/\r|\n/.test(match[0].slice(1, -1))) {
				return false;
			}
		}
		// Split selectorText by commas and validate each part
		var selectors = parseAndSplitNestedSelectors(selectorText);
		for (var i = 0; i < selectors.length; i++) {
			var processedSelectors = selectors[i].trim();
			if (!validateSelector(processedSelectors) || !validateNamespaceSelector(processedSelectors)) {
				return false;
			}
		}
		return true;
	}

	var endingIndex = token.length - 1;

	for (var character; (character = token.charAt(i)); i++) {
		if (i === endingIndex) {
			switch (state) {
				case "importRule":
				case "namespaceRule":
				case "layerBlock":
					token += ";"
			}
		}
		
		switch (character) {

		case " ":
		case "\t":
		case "\r":
		case "\n":
		case "\f":
			if (SIGNIFICANT_WHITESPACE[state]) {
				buffer += character;
			}
			break;

		// String
		case '"':
			index = i + 1;
			do {
				index = token.indexOf('"', index) + 1;
				if (!index) {
					parseError('Unmatched "');
				}
			} while (token[index - 2] === '\\');
			if (index === 0) {
				break;
			}
			buffer += token.slice(i, index);
			i = index - 1;
			switch (state) {
				case 'before-value':
					state = 'value';
					break;
				case 'importRule-begin':
					state = 'importRule';
					if (i === endingIndex) {
						token += ';'
					}
					break;
				case 'namespaceRule-begin':
					state = 'namespaceRule';
					if (i === endingIndex) {
						token += ';'
					}
					break;
			}
			break;

		case "'":
			index = i + 1;
			do {
				index = token.indexOf("'", index) + 1;
				if (!index) {
					parseError("Unmatched '");
				}
			} while (token[index - 2] === '\\');
			if (index === 0) {
				break;
			}
			buffer += token.slice(i, index);
			i = index - 1;
			switch (state) {
				case 'before-value':
					state = 'value';
					break;
				case 'importRule-begin':
					state = 'importRule';
					break;
				case 'namespaceRule-begin':
					state = 'namespaceRule';
					break;
			}
			break;

		// Comment
		case "/":
			if (token.charAt(i + 1) === "*") {
				i += 2;
				index = token.indexOf("*/", i);
				if (index === -1) {
					parseError("Missing */");
				} else {
					i = index + 1;
				}
			} else {
				buffer += character;
			}
			if (state === "importRule-begin") {
				buffer += " ";
				state = "importRule";
			}
			if (state === "namespaceRule-begin") {
				buffer += " ";
				state = "namespaceRule";
			}
			break;

		// At-rule
		case "@":
			if (token.indexOf("@-moz-document", i) === i) {
				validateAtRule("@-moz-document", function(){
					state = "documentRule-begin";
					documentRule = new CSSOM.CSSDocumentRule();
					documentRule.__starts = i;
					i += "-moz-document".length;
				});
				buffer = "";
				break;
			} else if (token.indexOf("@media", i) === i) {
				validateAtRule("@media", function(){
					state = "atBlock";
					mediaRule = new CSSOM.CSSMediaRule();
					mediaRule.__starts = i;
					i += "media".length;
				});
				buffer = "";
				break;
			} else if (token.indexOf("@container", i) === i) {
				validateAtRule("@container", function(){
					state = "containerBlock";
					containerRule = new CSSOM.CSSContainerRule();
					containerRule.__starts = i;
					i += "container".length;
				});
				buffer = "";
				break;
			} else if (token.indexOf("@counter-style", i) === i) {
				validateAtRule("@counter-style", function(){
					state = "counterStyleBlock"
					counterStyleRule = new CSSOM.CSSCounterStyleRule();
					counterStyleRule.__starts = i;
					i += "counter-style".length;
				}, true);
				buffer = "";
				break;
			} else if (token.indexOf("@layer", i) === i) {
				validateAtRule("@layer", function(){
					state = "layerBlock"
					layerBlockRule = new CSSOM.CSSLayerBlockRule();
					layerBlockRule.__starts = i;
					i += "layer".length;
				});
				buffer = "";
				break;
			} else if (token.indexOf("@supports", i) === i) {
				validateAtRule("@supports", function(){
					state = "conditionBlock";
					supportsRule = new CSSOM.CSSSupportsRule();
					supportsRule.__starts = i;
					i += "supports".length;
				});
				buffer = "";
				break;
			} else if (token.indexOf("@host", i) === i) {
				validateAtRule("@host", function(){
					state = "hostRule-begin";
					i += "host".length;
					hostRule = new CSSOM.CSSHostRule();
					hostRule.__starts = i;
				});
				buffer = "";
				break;
			} else if (token.indexOf("@starting-style", i) === i) {
				validateAtRule("@starting-style", function(){
					state = "startingStyleRule-begin";
					i += "starting-style".length;
					startingStyleRule = new CSSOM.CSSStartingStyleRule();
					startingStyleRule.__starts = i;
				});
				buffer = "";
				break;
			} else if (token.indexOf("@import", i) === i) {
				buffer = "";
				validateAtRule("@import", function(){
					state = "importRule-begin";
					i += "import".length;
					buffer += "@import";
				}, true);
				break;
			} else if (token.indexOf("@namespace", i) === i) {
				buffer = "";
				validateAtRule("@namespace", function(){
					state = "namespaceRule-begin";
					i += "namespace".length;
					buffer += "@namespace";
				}, true);
				break;
			} else if (token.indexOf("@font-face", i) === i) {
				buffer = "";
				validateAtRule("@font-face", function(){
					state = "fontFaceRule-begin";
					i += "font-face".length;
					fontFaceRule = new CSSOM.CSSFontFaceRule();
					fontFaceRule.__starts = i;
				}, true);
				break;
			} else {
				atKeyframesRegExp.lastIndex = i;
				var matchKeyframes = atKeyframesRegExp.exec(token);
				if (matchKeyframes && matchKeyframes.index === i) {
					state = "keyframesRule-begin";
					keyframesRule = new CSSOM.CSSKeyframesRule();
					keyframesRule.__starts = i;
					keyframesRule._vendorPrefix = matchKeyframes[1]; // Will come out as undefined if no prefix was found
					i += matchKeyframes[0].length - 1;
					buffer = "";
					break;
				} else if (state === "selector") {
					state = "atRule";
				}
			}
			buffer += character;
			break;

		case "{":
			if (currentScope === styleSheet) {
				nestedSelectorRule = null;
			}
			if (state === 'before-selector') {
				parseError("Unexpected {");
				i = ignoreBalancedBlock(i, token.slice(i));
				break;
			}
			if (state === "selector" || state === "atRule") {
				if (!nestedSelectorRule && buffer.indexOf(";") !== -1) {
					var ruleClosingMatch = token.slice(i).match(forwardRuleClosingBraceRegExp);
					if (ruleClosingMatch) {
						styleRule = null;
						buffer = "";
						state = "before-selector";
						i += ruleClosingMatch.index + ruleClosingMatch[0].length;
						break;
					}
				}

				if (parentRule) {
					styleRule.__parentRule = parentRule;
					ancestorRules.push(parentRule);
				}

				currentScope = parentRule = styleRule;
				styleRule.selectorText = buffer.trim().replace(/(['"])(?:\\.|[^\\])*?\1|(\r\n|\r|\n)/g, function(match, _, newline) {
					if (newline) return " ";
					return match;
				});
				styleRule.style.__starts = i;
				styleRule.__parentStyleSheet = styleSheet;
				buffer = "";
				state = "before-name";
			} else if (state === "atBlock") {
				mediaRule.media.mediaText = buffer.trim();

				if (parentRule) {
					mediaRule.__parentRule = parentRule;
					ancestorRules.push(parentRule);
				}

				currentScope = parentRule = mediaRule;
				mediaRule.__parentStyleSheet = styleSheet;
				buffer = "";
				state = "before-selector";
			} else if (state === "containerBlock") {
				containerRule.containerText = buffer.trim();

				if (parentRule) {
					containerRule.__parentRule = parentRule;
					ancestorRules.push(parentRule);
				}
				currentScope = parentRule = containerRule;
				containerRule.__parentStyleSheet = styleSheet;
				buffer = "";
				state = "before-selector";
			} else if (state === "counterStyleBlock") {
				// TODO: Validate counter-style name. At least that it cannot be empty nor multiple
				counterStyleRule.name = buffer.trim().replace(/\n/g, "");
				currentScope = parentRule = counterStyleRule;
				counterStyleRule.__parentStyleSheet = styleSheet;
				buffer = "";
			} else if (state === "conditionBlock") {
				supportsRule.conditionText = buffer.trim();

				if (parentRule) {
					supportsRule.__parentRule = parentRule;
					ancestorRules.push(parentRule);
				}

				currentScope = parentRule = supportsRule;
				supportsRule.__parentStyleSheet = styleSheet;
				buffer = "";
				state = "before-selector";
			} else if (state === "layerBlock") {
				layerBlockRule.name = buffer.trim();

				var isValidName = layerBlockRule.name.length === 0 || layerBlockRule.name.match(layerRuleNameRegExp) !== null;

				if (isValidName) {
					if (parentRule) {
						layerBlockRule.__parentRule = parentRule;
						ancestorRules.push(parentRule);
					}
	
					currentScope = parentRule = layerBlockRule;
					layerBlockRule.__parentStyleSheet = styleSheet;
				}
				buffer = "";
				state = "before-selector";
			} else if (state === "hostRule-begin") {
				if (parentRule) {
					ancestorRules.push(parentRule);
				}

				currentScope = parentRule = hostRule;
				hostRule.__parentStyleSheet = styleSheet;
				buffer = "";
				state = "before-selector";
			} else if (state === "startingStyleRule-begin") {
				if (parentRule) {
					startingStyleRule.__parentRule = parentRule;
					ancestorRules.push(parentRule);
				}

				currentScope = parentRule = startingStyleRule;
				startingStyleRule.__parentStyleSheet = styleSheet;
				buffer = "";
				state = "before-selector";

			} else if (state === "fontFaceRule-begin") {
				if (parentRule) {
					fontFaceRule.__parentRule = parentRule;
				}
				fontFaceRule.__parentStyleSheet = styleSheet;
				styleRule = fontFaceRule;
				buffer = "";
				state = "before-name";
			} else if (state === "keyframesRule-begin") {
				keyframesRule.name = buffer.trim();
				if (parentRule) {
					ancestorRules.push(parentRule);
					keyframesRule.__parentRule = parentRule;
				}
				keyframesRule.__parentStyleSheet = styleSheet;
				currentScope = parentRule = keyframesRule;
				buffer = "";
				state = "keyframeRule-begin";
			} else if (state === "keyframeRule-begin") {
				styleRule = new CSSOM.CSSKeyframeRule();
				styleRule.keyText = buffer.trim();
				styleRule.__starts = i;
				buffer = "";
				state = "before-name";
			} else if (state === "documentRule-begin") {
				// FIXME: what if this '{' is in the url text of the match function?
				documentRule.matcher.matcherText = buffer.trim();
				if (parentRule) {
					ancestorRules.push(parentRule);
					documentRule.__parentRule = parentRule;
				}
				currentScope = parentRule = documentRule;
				documentRule.__parentStyleSheet = styleSheet;
				buffer = "";
				state = "before-selector";
			} else if (state === "before-name" || state === "name") {
				if (styleRule.constructor.name === "CSSNestedDeclarations") {
					if (styleRule.style.length) {
						parentRule.cssRules.push(styleRule);
						styleRule.__parentRule = parentRule;
						styleRule.__parentStyleSheet = styleSheet;
						ancestorRules.push(parentRule);
					} else {
						// If the styleRule is empty, we can assume that it's a nested selector
						ancestorRules.push(parentRule);
					}
				} else {
					currentScope = parentRule = styleRule;
					ancestorRules.push(parentRule);
					styleRule.__parentStyleSheet = styleSheet;
				}
				
				styleRule = new CSSOM.CSSStyleRule();
				var processedSelectorText = buffer.trim().replace(/(['"])(?:\\.|[^\\])*?\1|(\r\n|\r|\n)/g, function(match, _, newline) {
					if (newline) return " ";
					return match;
				});
				// In a nested selector, ensure each selector contains '&' at the beginning, except for selectors that already have '&' somewhere
				if (parentRule.constructor.name !== "CSSStyleRule" && parentRule.parentRule === null) {
					styleRule.selectorText = processedSelectorText;
				} else {
					styleRule.selectorText = parseAndSplitNestedSelectors(processedSelectorText).map(function(sel) {
							return sel.indexOf('&') === -1 ? '& ' + sel : sel;
						}).join(', ');
				}
				styleRule.style.__starts = i - buffer.length;
				styleRule.__parentRule = parentRule;
				nestedSelectorRule = styleRule;

				buffer = "";
				state = "before-name";
			}
			break;

		case ":":
			if (state === "name") {
				// It can be a nested selector, let's check
				var openBraceBeforeMatch = token.slice(i).match(/[{;}]/);
				var hasOpenBraceBefore = openBraceBeforeMatch && openBraceBeforeMatch[0] === '{';
				if (hasOpenBraceBefore) {
					// Is a selector
					buffer += character;
				} else {
					// Is a declaration
					name = buffer.trim();
					buffer = "";
					state = "before-value";
				}
			} else {
				buffer += character;
			}
			break;

		case "(":
			if (state === 'value') {
				// ie css expression mode
				if (buffer.trim() === 'expression') {
					var info = (new CSSOM.CSSValueExpression(token, i)).parse();

					if (info.error) {
						parseError(info.error);
					} else {
						buffer += info.expression;
						i = info.idx;
					}
				} else {
					state = 'value-parenthesis';
					//always ensure this is reset to 1 on transition
					//from value to value-parenthesis
					valueParenthesisDepth = 1;
					buffer += character;
				}
			} else if (state === 'value-parenthesis') {
				valueParenthesisDepth++;
				buffer += character;
			} else {
				buffer += character;
			}
			break;

		case ")":
			if (state === 'value-parenthesis') {
				valueParenthesisDepth--;
				if (valueParenthesisDepth === 0) state = 'value';
			}
			buffer += character;
			break;

		case "!":
			if (state === "value" && token.indexOf("!important", i) === i) {
				priority = "important";
				i += "important".length;
			} else {
				buffer += character;
			}
			break;

		case ";":
			switch (state) {
				case "before-value":
				case "before-name":
					parseError("Unexpected ;");
					buffer = "";
					state = "before-name";
					break;
				case "value":
					styleRule.style.setProperty(name, buffer.trim(), priority, parseError);
					priority = "";
					buffer = "";
					state = "before-name";
					break;
				case "atRule":
					buffer = "";
					state = "before-selector";
					break;
				case "importRule":
					var isValid = styleSheet.cssRules.length === 0 || styleSheet.cssRules.some(function (rule) {
						return ['CSSImportRule', 'CSSLayerStatementRule'].indexOf(rule.constructor.name) !== -1
					});
					if (isValid) {
						importRule = new CSSOM.CSSImportRule();
						importRule.__parentStyleSheet = importRule.styleSheet.__parentStyleSheet = styleSheet;
						importRule.cssText = buffer + character;
						styleSheet.cssRules.push(importRule);
					}
					buffer = "";
					state = "before-selector";
					break;
				case "namespaceRule":
					var isValid = styleSheet.cssRules.length === 0 || styleSheet.cssRules.every(function (rule) {
						return ['CSSImportRule','CSSLayerStatementRule','CSSNamespaceRule'].indexOf(rule.constructor.name) !== -1
					});
					if (isValid) {
						try {
							// Validate namespace syntax before creating the rule
							var testNamespaceRule = new CSSOM.CSSNamespaceRule();
							testNamespaceRule.cssText = buffer + character;
							
							namespaceRule = testNamespaceRule;
							namespaceRule.__parentStyleSheet = namespaceRule.styleSheet.__parentStyleSheet = styleSheet;
							styleSheet.cssRules.push(namespaceRule);
							
							// Track the namespace prefix for validation
							if (namespaceRule.prefix) {
								definedNamespacePrefixes[namespaceRule.prefix] = namespaceRule.namespaceURI;
							}
						} catch(e) {
							parseError(e.message);
						}
					}
					buffer = "";
					state = "before-selector";
					break;
				case "layerBlock":
					var nameListStr = buffer.trim().split(",").map(function (name) {
						return name.trim();
					});
					var isInvalid = parentRule !== undefined || nameListStr.some(function (name) {
						return name.trim().match(layerRuleNameRegExp) === null;
					});

					if (!isInvalid) {
						layerStatementRule = new CSSOM.CSSLayerStatementRule();
						layerStatementRule.__parentStyleSheet = styleSheet;
						layerStatementRule.__starts = layerBlockRule.__starts;
						layerStatementRule.__ends = i;
						layerStatementRule.nameList = nameListStr;
						styleSheet.cssRules.push(layerStatementRule);
					}
					buffer = "";
					state = "before-selector";
					break;
				default:
					buffer += character;
					break;
			}
			break;

		case "}":
			if (state === "counterStyleBlock") {
				// FIXME : Implement cssText get setter that parses the real implementation
				counterStyleRule.cssText = "@counter-style " + counterStyleRule.name + " { " + buffer.trim().replace(/\n/g, " ").replace(/(['"])(?:\\.|[^\\])*?\1|(\s{2,})/g, function(match, quote) {
					return quote ? match : ' ';
				}) + " }";
				buffer = "";
				state = "before-selector";
			}

			switch (state) {
				case "value":
					styleRule.style.setProperty(name, buffer.trim(), priority, parseError);
					priority = "";
					/* falls through */
				case "before-value":
				case "before-name":
				case "name":
					styleRule.__ends = i + 1;
					
					if (parentRule === styleRule) {
						parentRule = ancestorRules.pop()
					}

					if (parentRule) {
						styleRule.__parentRule = parentRule;
					}
					styleRule.__parentStyleSheet = styleSheet;

					if (currentScope === styleRule) {
						currentScope = parentRule || styleSheet;
					}

					if (styleRule.constructor.name === "CSSStyleRule" && !isValidSelectorText(styleRule.selectorText)) {
						if (styleRule === nestedSelectorRule) {
							nestedSelectorRule = null;
						}
						parseError('Invalid CSSStyleRule (selectorText = "' + styleRule.selectorText + '")');
					} else {
						currentScope.cssRules.push(styleRule);
					}
					buffer = "";
					if (currentScope.constructor === CSSOM.CSSKeyframesRule) {
						state = "keyframeRule-begin";
					} else {
						state = "before-selector";
					}

					if (styleRule.constructor.name === "CSSNestedDeclarations") {
						if (currentScope !== styleSheet) {
							nestedSelectorRule = currentScope;
						}
						styleRule = null;
					} else {
						styleRule = null;
						break;
					}
				case "keyframeRule-begin":
				case "before-selector":
				case "selector":
					// End of media/supports/document rule.
					if (!parentRule) {
						parseError("Unexpected }");
						
						var hasPreviousStyleRule = currentScope.cssRules.length && currentScope.cssRules[currentScope.cssRules.length - 1].constructor.name === "CSSStyleRule";
						if (hasPreviousStyleRule) {
							i = ignoreBalancedBlock(i, token.slice(i), 1);
						}
						
						break;
					}


					while (ancestorRules.length > 0) {
						parentRule = ancestorRules.pop();

						if (
							parentRule.constructor.name === "CSSStyleRule"
							|| parentRule.constructor.name === "CSSMediaRule"
							|| parentRule.constructor.name === "CSSSupportsRule"
							|| parentRule.constructor.name === "CSSContainerRule"
							|| parentRule.constructor.name === "CSSLayerBlockRule"
							|| parentRule.constructor.name === "CSSStartingStyleRule"
						) {
							if (nestedSelectorRule) {
								if (nestedSelectorRule.parentRule) {
									prevScope = nestedSelectorRule;
									currentScope = nestedSelectorRule.parentRule;
									if (currentScope.cssRules.findIndex(function (rule) {
										return rule === prevScope
									}) === -1) {
										currentScope.cssRules.push(prevScope);
									}
									nestedSelectorRule = currentScope;
								}
							} else {
								prevScope = currentScope;
								currentScope = parentRule;
								currentScope !== prevScope && currentScope.cssRules.push(prevScope);
								break;
							}
						}
					}
					
					if (currentScope.parentRule == null) {
						currentScope.__ends = i + 1;
						if (currentScope !== styleSheet && styleSheet.cssRules.findIndex(function (rule) {
							return rule === currentScope
						}) === -1) {
							styleSheet.cssRules.push(currentScope);
						}
						currentScope = styleSheet;
						if (nestedSelectorRule === parentRule) {
							// Check if this selector is really starting inside another selector
							var nestedSelectorTokenToCurrentSelectorToken = token.slice(nestedSelectorRule.__starts, i + 1);
							var openingBraceMatch = nestedSelectorTokenToCurrentSelectorToken.match(/{/g);
							var closingBraceMatch = nestedSelectorTokenToCurrentSelectorToken.match(/}/g);
							var openingBraceLen = openingBraceMatch && openingBraceMatch.length;
							var closingBraceLen = closingBraceMatch && closingBraceMatch.length;

							if (openingBraceLen === closingBraceLen) {
								// If the number of opening and closing braces are equal, we can assume that the new selector is starting outside the nestedSelectorRule
								nestedSelectorRule.__ends = i + 1;
								nestedSelectorRule = null;
								parentRule = null;
							}
						} else {
							parentRule = null;

						}
					}

					buffer = "";
					state = "before-selector";
					break;
			}
			break;

		default:
			switch (state) {
				case "before-selector":
					state = "selector";
					if (styleRule && parentRule) {
						// Assuming it's a declaration inside Nested Selector OR a Nested Declaration
						// If Declaration inside Nested Selector let's keep the same styleRule
						if (
							parentRule.constructor.name === "CSSStyleRule"
							|| parentRule.constructor.name === "CSSMediaRule"
							|| parentRule.constructor.name === "CSSSupportsRule"
							|| parentRule.constructor.name === "CSSContainerRule"
							|| parentRule.constructor.name === "CSSLayerBlockRule"
							|| parentRule.constructor.name === "CSSStartingStyleRule"
						) {
							// parentRule.__parentRule = styleRule;
							state = "before-name";
							if (styleRule !== parentRule) {
								styleRule = new CSSOM.CSSNestedDeclarations();
								styleRule.__starts = i;	
							}
						}
						
					} else if (nestedSelectorRule && parentRule && (
						parentRule.constructor.name === "CSSStyleRule"
						|| parentRule.constructor.name === "CSSMediaRule"
						|| parentRule.constructor.name === "CSSSupportsRule"
						|| parentRule.constructor.name === "CSSContainerRule"
						|| parentRule.constructor.name === "CSSLayerBlockRule"
						|| parentRule.constructor.name === "CSSStartingStyleRule"
					)) {
						state = "before-name";
						if (parentRule.cssRules.length) {
							currentScope = nestedSelectorRule = parentRule;
							styleRule = new CSSOM.CSSNestedDeclarations();
							styleRule.__starts = i;	
						} else {
							if (parentRule.constructor.name === "CSSStyleRule") {
								styleRule = parentRule;
							} else {
								styleRule = new CSSOM.CSSStyleRule();
								styleRule.__starts = i;								
							}
						}
					} else {
						styleRule = new CSSOM.CSSStyleRule();
						styleRule.__starts = i;
					}
					break;
				case "before-name":
					state = "name";
					break;
				case "before-value":
					state = "value";
					break;
				case "importRule-begin":
					state = "importRule";
					break;
				case "namespaceRule-begin":
					state = "namespaceRule";
					break;
			}
			buffer += character;
			break;
		}
	}

	return styleSheet;
};


//.CommonJS
exports.parse = CSSOM.parse;
// The following modules cannot be included sooner due to the mutual dependency with parse.js
CSSOM.CSSStyleSheet = require("./CSSStyleSheet").CSSStyleSheet;
CSSOM.CSSStyleRule = require("./CSSStyleRule").CSSStyleRule;
CSSOM.CSSNestedDeclarations = require("./CSSNestedDeclarations").CSSNestedDeclarations;
CSSOM.CSSImportRule = require("./CSSImportRule").CSSImportRule;
CSSOM.CSSNamespaceRule = require("./CSSNamespaceRule").CSSNamespaceRule;
CSSOM.CSSGroupingRule = require("./CSSGroupingRule").CSSGroupingRule;
CSSOM.CSSMediaRule = require("./CSSMediaRule").CSSMediaRule;
CSSOM.CSSCounterStyleRule = require("./CSSCounterStyleRule").CSSCounterStyleRule;
CSSOM.CSSContainerRule = require("./CSSContainerRule").CSSContainerRule;
CSSOM.CSSConditionRule = require("./CSSConditionRule").CSSConditionRule;
CSSOM.CSSSupportsRule = require("./CSSSupportsRule").CSSSupportsRule;
CSSOM.CSSFontFaceRule = require("./CSSFontFaceRule").CSSFontFaceRule;
CSSOM.CSSHostRule = require("./CSSHostRule").CSSHostRule;
CSSOM.CSSStartingStyleRule = require("./CSSStartingStyleRule").CSSStartingStyleRule;
CSSOM.CSSStyleDeclaration = require('./CSSStyleDeclaration').CSSStyleDeclaration;
CSSOM.CSSKeyframeRule = require('./CSSKeyframeRule').CSSKeyframeRule;
CSSOM.CSSKeyframesRule = require('./CSSKeyframesRule').CSSKeyframesRule;
CSSOM.CSSValueExpression = require('./CSSValueExpression').CSSValueExpression;
CSSOM.CSSDocumentRule = require('./CSSDocumentRule').CSSDocumentRule;
CSSOM.CSSLayerBlockRule = require("./CSSLayerBlockRule").CSSLayerBlockRule;
CSSOM.CSSLayerStatementRule = require("./CSSLayerStatementRule").CSSLayerStatementRule;
// Use cssstyle if available
try {
	CSSOM.CSSStyleDeclaration = require("cssstyle").CSSStyleDeclaration;
} catch (e) {
	// ignore
}
///CommonJS
