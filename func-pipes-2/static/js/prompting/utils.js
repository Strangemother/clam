

const dispatchEvent = function(name, detail, parent=window){
    let e = new CustomEvent(name, { detail });
    parent.dispatchEvent(e)
    return e;
}

const listenEvent = function(name, handler, parent=window) {
    parent.addEventListener(name, handler)
}

const copyHTML = function(selector) {
    return document.querySelector(selector).innerHTML
}

const getTemplateHTML = function(selector) {
  return copyHTML(`.templates .panel-template ${selector}`)
}
