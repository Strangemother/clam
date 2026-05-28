
const FunctionCall = Object.assign({}, NodeBase, {
    // props: ['uuid', 'panel']
    data() {
        return {
            userText: `console.log("inner", panel.id, pip, data, this); return parseInt(data) + 10`
        }
    }
    , template: getTemplateHTML('.function-call')
    , methods: Object.assign({}, PanelBaseMethods, {
        customCallback(data, pip) {
            // somehow called be the spawnpanel callback.
            console.log('func customCallback', data, pip)
            try{
                let f = Function(
                     `function runUserContent(data, pip, panel) {
                         ${this.userText}
                      }; return runUserContent`,

                )
                let res = f.apply(this).apply(this, [data, pip, this.panel]);
                // console.log(res)
                return res
            }catch(err) {
                console.warn('Node fail', err)
            }
            return data + 10
        }
    })
});

nodeRegister.FunctionCall = FunctionCall

