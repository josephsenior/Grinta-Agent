//.CommonJS
var CSSOM = {
	CSSRule: require("./CSSRule").CSSRule,
	CSSStyleSheet: require("./CSSStyleSheet").CSSStyleSheet,
	MediaList: require("./MediaList").MediaList
};
///CommonJS


/**
 * @constructor
 * @see http://dev.w3.org/csswg/cssom/#cssimportrule
 * @see http://www.w3.org/TR/DOM-Level-2-Style/css.html#CSS-CSSImportRule
 */
CSSOM.CSSImportRule = function CSSImportRule() {
	CSSOM.CSSRule.call(this);
	this.href = "";
	this.media = new CSSOM.MediaList();
  this.layerName = null;
  this.supportsText = null;
	this.styleSheet = new CSSOM.CSSStyleSheet();
};

CSSOM.CSSImportRule.prototype = new CSSOM.CSSRule();
CSSOM.CSSImportRule.prototype.constructor = CSSOM.CSSImportRule;
CSSOM.CSSImportRule.prototype.type = 3;

Object.defineProperty(CSSOM.CSSImportRule.prototype, "cssText", {
  get: function() {
    var mediaText = this.media.mediaText;
    return "@import url(\"" + this.href + "\")" + (this.layerName !== null ? " layer" + (this.layerName && "(" + this.layerName + ")") : "" ) + (this.supportsText ? " supports(" + this.supportsText + ")" : "" ) + (mediaText ? " " + mediaText : "") + ";";
  },
  set: function(cssText) {
    var i = 0;

    /**
     * @import url(partial.css) screen, handheld;
     *        ||               |
     *        after-import     media
     *         |
     *         url
     */
    var state = '';

    var buffer = '';
    var index;

    var layerRegExp = /layer\(([^)]*)\)/;
    var layerRuleNameRegExp = /^(-?[_a-zA-Z]+(\.[_a-zA-Z]+)*[_a-zA-Z0-9-]*)$/;
    var supportsRegExp = /supports\(([^)]+)\)/;
    var doubleOrMoreSpacesRegExp = /\s{2,}/g;

    for (var character; (character = cssText.charAt(i)); i++) {

      switch (character) {
        case ' ':
        case '\t':
        case '\r':
        case '\n':
        case '\f':
          if (state === 'after-import') {
            state = 'url';
          } else {
            buffer += character;
          }
          break;

        case '@':
          if (!state && cssText.indexOf('@import', i) === i) {
            state = 'after-import';
            i += 'import'.length;
            buffer = '';
          }
          break;

        case 'u':
          if (state === 'media') {
            buffer += character;
          }
          if (state === 'url' && cssText.indexOf('url(', i) === i) {
            index = cssText.indexOf(')', i + 1);
            if (index === -1) {
              throw i + ': ")" not found';
            }
            i += 'url('.length;
            var url = cssText.slice(i, index);
            if (url[0] === url[url.length - 1]) {
              if (url[0] === '"' || url[0] === "'") {
                url = url.slice(1, -1);
              }
            }
            this.href = url;
            i = index;
            state = 'media';
          }
          break;

        case '"':
          if (state === 'after-import' || state === 'url') {
            index = cssText.indexOf('"', i + 1);
            if (!index) {
              throw i + ": '\"' not found";
            }
            this.href = cssText.slice(i + 1, index);
            i = index;
            state = 'media';
          }
          break;

        case "'":
          if (state === 'after-import' || state === 'url') {
            index = cssText.indexOf("'", i + 1);
            if (!index) {
              throw i + ': "\'" not found';
            }
            this.href = cssText.slice(i + 1, index);
            i = index;
            state = 'media';
          }
          break;

        case ';':
          if (state === 'media') {
            if (buffer) {
              var bufferTrimmed = buffer.trim();
              
              if (bufferTrimmed.indexOf('layer') === 0) {
                var layerMatch =  bufferTrimmed.match(layerRegExp);

                if (layerMatch) {
                  var layerName = layerMatch[1].trim();

                  if (layerName.match(layerRuleNameRegExp) !== null) {
                    this.layerName = layerMatch[1].trim();
                    bufferTrimmed = bufferTrimmed.replace(layerRegExp, '')
                      .replace(doubleOrMoreSpacesRegExp, ' ') // Replace double or more spaces with single space
                      .trim();
                  } else {
                    // REVIEW: In the browser, an empty layer() is not processed as a unamed layer
                    // and treats the rest of the string as mediaText, ignoring the parse of supports()
                    if (bufferTrimmed) {
                      this.media.mediaText = bufferTrimmed;
                      return;
                    }
                  }
                } else {
                  this.layerName = "";
                  bufferTrimmed = bufferTrimmed.substring('layer'.length).trim()
                }
              }

              var supportsMatch =  bufferTrimmed.match(supportsRegExp);

              if (supportsMatch && supportsMatch.index === 0) {
                // REVIEW: In the browser, an empty supports() invalidates and ignores the entire @import rule
                this.supportsText = supportsMatch[1].trim();
                bufferTrimmed = bufferTrimmed.replace(supportsRegExp, '')
                .replace(doubleOrMoreSpacesRegExp, ' ') // Replace double or more spaces with single space
                .trim();
              }

              // REVIEW: In the browser, any invalid media is replaced with 'not all'
              if (bufferTrimmed) {
                this.media.mediaText = bufferTrimmed;
              }
            }
          }
          break;

        default:
          if (state === 'media') {
            buffer += character;
          }
          break;
      }
    }
  }
});


//.CommonJS
exports.CSSImportRule = CSSOM.CSSImportRule;
///CommonJS
