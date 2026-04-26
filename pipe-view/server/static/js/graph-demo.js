const spawnDemoWindows = function(appRef) {
    if(appRef == undefined) {
        return
    }

    const randomPercent = function(max=80) {
        return `${Math.floor(Math.random() * (max + 1))}%`
    }

    let names = [
        'apples',
        'banana',
        'cherry',
        'date',
        'elderberry',
        'fig',
        'grape',
        'honeydew',
        'kiwi',
        'lemon'
    ]

    names.forEach((name)=>{
        appRef.spawnWindow({
            name,
            x: randomPercent(),
            y: randomPercent()
        })
    })
}


const autoConnectDemoNodes = function(layerGroup) {
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
    setTimeout(()=>{
        autoConnectDemoNodes(layerGroup)
    }, 300)
}


bootDemoGraph()


window.bootDemoGraph = bootDemoGraph
window.spawnDemoWindows = spawnDemoWindows
window.autoConnectDemoNodes = autoConnectDemoNodes
