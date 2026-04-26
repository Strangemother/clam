
class WorkTasks {
    /*
    This is a scratch area for testing out code related to graph traversal and highlighting,
    demo graph setup, and the PipesTool wrapper class.
    It's not meant to be a permanent part of the codebase,
    but it can be useful for iterating on these features in the context of the
    full app before deciding what to keep and what to discard.
    */
    constructor(){
        console.log('WorkTasks initialized')
    }

    banana(config, data) {
        console.log('Banana task executed', config)
        return this.defaultTask(config, data)
    }

    cherry(config, data){
        console.log('cherry');
        return this.defaultTask(config, data)
    }
    date(config, data){
        console.log('date');
        return this.defaultTask(config, data)
    }
    elderberry(config, data){
        console.log('elderberry');
        return this.defaultTask(config, data)
    }
    fig(config, data){
       console.log('fig');
       return this.defaultTask(config, data)
    }
    grape(config, data){
        console.log('grape');
        return this.defaultTask(config, data)
    }
    honeydew(config, data){
        console.log('honeydew');
        return this.defaultTask(config, data)
    }
    kiwi(config, data){
        console.log('kiwi');
        return this.defaultTask(config, data)
    }
    lemon(config, data){
        console.log('lemon');
        return this.defaultTask(config, data)
    }

    defaultTask(config, data) {
        // If a task is not coded, this is executed.
        console.log('Default task executed', config)
        let res = data + 2
        config.viewInfo.words = res;
        return res;
    }
}


const spawnDemoWindows = function(appRef) {
    if(appRef == undefined) {
        return
    }

    const randomPercent = function(max=80) {
        return `${Math.floor(Math.random() * (max + 1))}%`
    }

    let nodes = [
        { name: 'apples', x: 60, y: 60 }
        , { name: 'banana', exampleData: 123 }
        , { name: 'cherry'}
        , { name: 'date'}
        , { name: 'elderberry'}
        , { name: 'fig'}
        , { name: 'grape'}
        , { name: 'honeydew'}
        , { name: 'kiwi'}
        , { name: 'lemon'}
    ]

    nodes.forEach((item)=>{
        appRef.spawnWindow(
            Object.assign({
                x: randomPercent()
                , y: randomPercent()
            }, item)
        )
    })
}


const autoConnectDemoNodes = function(layerGroup) {
    /* An example of some cheap connection

        setTimeout(()=>{
            autoConnectDemoNodes(layerGroup)
        }, 300)

    run it in `bootDemoGraph` for an example.
    */
    if(layerGroup == undefined) {
        return
    }

    let ordered = {
        sender: {
            label: 'apples',
            direction: 'outbound',
            pipIndex: 0
        },
        receiver: {
            label: 'cherry',
            direction: 'inbound',
            pipIndex: 0
        }
    }

    layerGroup.connectNodes(ordered)
}


const bootDemoGraph = function(appRef=app, layerGroup=clItems) {
    if(appRef == undefined || layerGroup == undefined) {
        return
    }

    spawnDemoWindows(appRef)

}
