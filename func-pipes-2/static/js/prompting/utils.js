const PanelBaseMethods = {

        addInboundPip(panel) {
            panel.pipsInbound.push({
                name: Math.random().toString(32).slice(3),
                execute: false
            })
        }

        , addOutboundPip(panel) {
            panel.pipsOutbound.push({
              name: Math.random().toString(32).slice(3)
            })
        }

        , pipClick($event, panel, pip, i) {
            console.log(event, panel)
            // window.dispatchEvent(new CustomEvent('pipclick', {
            //     detail: {
            //         panel
            //         , pip
            //         , i
            //     }
            // }))
            dispatchEvent('pipclick', {
                    panel
                    , pip
                    , i
                })
        }

}


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
