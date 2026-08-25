/**
 * jQuery json-viewer
 * @author: Alexandre Bodelot <alexandre.bodelot@gmail.com>, forked by Simon Dupouy
 * @link: https://github.com/sdupouy/jquery.json-viewer
 */
(function($) {

  /**
   * Check if arg is either an array with at least 1 element, or a dict with at least 1 key
   * @return boolean
   */
  function isCollapsable(arg) {
    return arg instanceof Object && Object.keys(arg).length > 0;
  }

  /**
   * Check if a string looks like a URL, based on protocol
   * This doesn't attempt to validate URLs, there's no use and syntax can be too complex
   * @return boolean
   */
  function isUrl(string) {
    var protocols = ['http', 'https', 'ftp', 'ftps'];
    for (var i = 0; i < protocols.length; ++i) {
      if (string.startsWith(protocols[i] + '://')) {
        return true;
      }
    }
    return false;
  }

  /**
   * Return the input string html escaped
   * @return string
   */
  function htmlEscape(s) {
    return s.replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/'/g, '&apos;')
      .replace(/"/g, '&quot;');
  }

  /**
   * Check if the value should be rendered as a big number literal
   * @return boolean
   */
  function isBigNumber(value, options) {
    return options.bigNumbers && value &&
      (typeof value.toExponential === 'function' || value.isLosslessNumber);
  }

  /**
   * Return the html for a copy button
   * @return string
   */
  function getCopyButton(path, options) {
    if (!options.copyToClipboard) {
      return '';
    }

    return ' <a href class="json-copy" data-path=\'' +
      htmlEscape(JSON.stringify(path)) + '\' title="Copy">&#x29C9;</a>';
  }

  /**
   * Resolve a path against the input json object
   * @return any
   */
  function getJsonValue(json, path) {
    for (var i = 0; i < path.length; ++i) {
      json = json[path[i]];
    }
    return json;
  }

  /**
   * Stringify json values while preserving displayed bigints and big numbers
   * @return string|undefined
   */
  function stringifyJsonValue(value, indentation, options) {
    return JSON.stringify(value, function(key, currentValue) {
      if (typeof currentValue === 'bigint') {
        return currentValue.toString();
      }
      if (isBigNumber(currentValue, options)) {
        return currentValue.toString();
      }
      return currentValue;
    }, indentation);
  }

  /**
   * Format a value for the clipboard
   * @return string|undefined
   */
  function getClipboardValue(value, options) {
    if (typeof value === 'string') {
      return value;
    }
    if (typeof value === 'number') {
      return String(value);
    }
    if (typeof value === 'bigint') {
      return value.toString();
    }
    if (typeof value === 'boolean') {
      return String(value);
    }
    if (value === null) {
      return 'null';
    }
    if (value instanceof Array) {
      return stringifyJsonValue(value, 0, options);
    }
    if (typeof value === 'object') {
      if (isBigNumber(value, options)) {
        return value.toString();
      }
      return stringifyJsonValue(value, 2, options);
    }
    return undefined;
  }

  /**
   * Copy a string to the clipboard
   * @return boolean|Promise<boolean>
   */
  function copyText(text) {
    if (navigator.clipboard &&
        typeof navigator.clipboard.writeText === 'function') {
      return navigator.clipboard.writeText(text).then(function() {
        return true;
      }, function() {
        return false;
      });
    }

    var textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'fixed';
    textarea.style.top = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    var success = false;
    try {
      success = document.execCommand('copy');
    } catch (error) {
      success = false;
    }
    document.body.removeChild(textarea);
    return success;
  }

  /**
   * Transform a json object into html representation
   * @return string
   */
  function json2html(json, options, path) {
    var html = '';
    if (typeof json === 'string') {
      // Escape tags and quotes
      json = htmlEscape(json);

      if (options.withLinks && isUrl(json)) {
        html += '<a href="' + json + '" class="json-string" target="_blank">' + json + '</a>';
      } else {
        // Escape double quotes in the rendered non-URL string.
        json = json.replace(/&quot;/g, '\\&quot;');
        html += '<span class="json-string">"' + json + '"</span>';
      }
    } else if (typeof json === 'number' || typeof json === 'bigint') {
      html += '<span class="json-literal">' + json + '</span>';
    } else if (typeof json === 'boolean') {
      html += '<span class="json-literal">' + json + '</span>';
    } else if (json === null) {
      html += '<span class="json-literal">null</span>';
    } else if (json instanceof Array) {
      if (json.length > 0) {
        html += '[<ol class="json-array">';
        for (var i = 0; i < json.length; ++i) {
          var itemPath = path.concat(i);
          html += '<li>';
          // Add toggle button if item is collapsable
          if (isCollapsable(json[i])) {
            html += '<a href class="json-toggle"></a>';
          }
          html += json2html(json[i], options, itemPath);
          // Add comma if item is not last
          if (i < json.length - 1) {
            html += ',';
          }
          html += getCopyButton(itemPath, options);
          html += '</li>';
        }
        html += '</ol>]';
      } else {
        html += '[]';
      }
    } else if (typeof json === 'object') {
      // Optional support different libraries for big numbers
      // json.isLosslessNumber: package lossless-json
      // json.toExponential(): packages bignumber.js, big.js, decimal.js, decimal.js-light, others?
      if (isBigNumber(json, options)) {
        html += '<span class="json-literal">' + json.toString() + '</span>';
      } else {
        var keyCount = Object.keys(json).length;
        if (keyCount > 0) {
          html += '{<ul class="json-dict">';
          for (var key in json) {
            if (Object.prototype.hasOwnProperty.call(json, key)) {
              var keyPath = path.concat(key);
              // define a parameter of the json value first to prevent get null from key when the key changed by the function `htmlEscape(key)`
              var jsonElement = json[key];
              var escapedKey = htmlEscape(key);
              var keyRepr = options.withQuotes
                ? '<span class="json-string">"' + escapedKey + '"</span>'
                : escapedKey;

              html += '<li>';
              // Add toggle button if item is collapsable
              if (isCollapsable(jsonElement)) {
                html += '<a href class="json-toggle">' + keyRepr + '</a>';
              } else {
                html += keyRepr;
              }
              html += ': ' + json2html(jsonElement, options, keyPath);
              // Add comma if item is not last
              if (--keyCount > 0) {
                html += ',';
              }
              html += getCopyButton(keyPath, options);
              html += '</li>';
            }
          }
          html += '</ul>}';
        } else {
          html += '{}';
        }
      }
    }
    return html;
  }

  /**
   * jQuery plugin method
   * @param json: a javascript object
   * @param options: an optional options hash
   */
  $.fn.jsonViewer = function(json, options) {
    // Merge user options with default options
    options = Object.assign({}, {
      collapsed: false,
      rootCollapsable: true,
      withQuotes: false,
      withLinks: true,
      bigNumbers: false,
      copyToClipboard: false
    }, options);

    // jQuery chaining
    return this.each(function() {
      var root = $(this);

      // Transform to HTML
      var html = json2html(json, options, []);
      html += getCopyButton([], options);
      if (options.rootCollapsable && isCollapsable(json)) {
        html = '<a href class="json-toggle"></a>' + html;
      }

      // Insert HTML in target DOM element
      root.html(html);
      root.addClass('json-document');
      root.data('json', json);

      // Bind click on toggle buttons
      root.off('click');
      root.on('click', 'a.json-toggle', function() {
        var target = $(this).toggleClass('collapsed')
          .siblings('ul.json-dict, ol.json-array');
        target.toggle();
        if (target.is(':visible')) {
          target.siblings('.json-placeholder').remove();
        } else {
          var count = target.children('li').length;
          var placeholder = count + (count > 1 ? ' items' : ' item');
          target.after('<a href class="json-placeholder">' + placeholder + '</a>');
        }
        return false;
      });

      // Simulate click on toggle button when placeholder is clicked
      root.on('click', 'a.json-placeholder', function() {
        $(this).siblings('a.json-toggle').click();
        return false;
      });

      // Copy a node value to the clipboard
      root.on('click', 'a.json-copy', function() {
        var path = JSON.parse($(this).attr('data-path'));
        var value = getJsonValue(root.data('json'), path);
        var text = getClipboardValue(value, options);
        if (text !== undefined) {
          copyText(text);
        }
        return false;
      });

      if (options.collapsed == true) {
        // Trigger click to collapse all nodes
        root.find('a.json-toggle').click();
      }
    });
  };
})(jQuery);