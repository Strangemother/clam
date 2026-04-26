
const createMiniApp = function() {
    /*
        Buttons
    */

    const localOrDefault = function(name, defaultName){
        if(localStorage[name] == undefined) {
            return defaultName
        }

        return localStorage[name]
    }

    const saveLocalStore = function(key, value) {
        localStorage[key] = value
    }

    const reactive = PetiteVue.reactive
    let app = {
        content: "apples"
        , services: reactive({
            items: []
        })
        , submitting: reactive(false)
        , responseData: reactive({ response: 'Nothing Yet' })
        , selectedService: reactive({ name: 'no name'})
        , getService(name) {
            /*
                @click=getService(service.name)
            */
            console.log('Load', name)
            this.selectedService.name = name;
            loadServiceByIndex(name, (d)=>{
                this.services[name] = d
                // this.services[name].models = d
                console.log('Loaded', name, d)
            })
        }
        , setModelName(name) {
            console.log('Name', name)
            this.selectedService.model = name
        }
        , formSubmit(ev) {
            ev.preventDefault()
            this.submitting = true
            let form = ev.currentTarget
            let d = new FormData(form)
            console.log(d.keys())
            saveLocalStore('v1SelectedDefaultName', d.get('name'))
            saveLocalStore('v1SelectedDefaultPrompt', d.get('prompt'))

            fetch(form.action, {
                method: "POST",
                body: d,
            }).then((d)=>{
                this.submitting = false
                return d
            }).then(d=>d.json()).then(this.presentForm.bind(this))

            return false
        }
        , presentForm(data) {
            this.responseData.files = []
            this.$nextTick(()=>{
                /*
                A tick must occur here, else the change reactive state of the
                (above) won't work.
                */
                console.log('Writing', data)
                for(let key in data) {
                    this.responseData[key] = data[key]
                }
            })
            // let resp = data.response
            // this.responseData.response = resp
        }
    }

    loadServices((data)=>{
        console.log('fetched', data)
        app.services.items = data.items
        app.selectedService.name = localOrDefault('v1SelectedDefaultName', data.default)
    })

    const res = PetiteVue.createApp(app)
    res.mount('#mini-app')

    let textAreaValue = localOrDefault('v1SelectedDefaultPrompt', '')
    app.$refs.prompt.value = textAreaValue

    return app

    // return res
}

const loadServices = function(callback) {
    return fetch('v1/services/').then(d=>d.json()).then(callback)
}

const loadServiceByIndex = function(name, callback) {
    return fetch(`v1/services/${name}/`).then(d=>d.json()).then(callback)
}


let app = createMiniApp();