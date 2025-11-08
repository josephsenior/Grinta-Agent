//.CommonJS
var CSSOM = {};
///CommonJS


/**
 * @constructor
 * @see http://dev.w3.org/csswg/cssom/#the-stylesheet-interface
 */
CSSOM.StyleSheet = function StyleSheet() {
	this.__parentStyleSheet = null;
};

Object.defineProperties(CSSOM.StyleSheet.prototype, {
	parentStyleSheet: {
		get: function() {
			return this.__parentStyleSheet;
		}
	}
});

//.CommonJS
exports.StyleSheet = CSSOM.StyleSheet;
///CommonJS
