const copyHTML = function(selector) {
    return document.querySelector(selector).innerHTML
}

const getTemplateHTML = function(selector) {
  return copyHTML(`.templates .panel-template ${selector}`)
}
