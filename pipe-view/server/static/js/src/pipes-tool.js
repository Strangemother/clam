/*
The PipeTool is the convience wrapper to capture all assets for the view.

- app: the view app
- walker: An executor
- lights: the highlighter tool
- layerGroup: the canvas manager

Then some convenience tools.

The vue app executes functonality through this.
*/

class PipesTool {
    //  user tool to access all the bits easily.
    filename = 'pipes-tool-graph'
    constructor(conf={}) {
        this.app = conf.app || app
        this.walker = conf.walker || new GraphExecutor({ taskMap: new WorkTasks() })
        this.lights = new GraphHighlighter({ app: this.app, walker: this.walker })
        this.layerGroup = conf.layerGroup || clItems
    }

    draw(){
        this.layerGroup.draw.apply(this.layerGroup, arguments)
    }


    save(name = this.filename) {
        // simple save method
        this.walker.saveToLocalStorage(name)
    }

    restore(name = this.filename) {
        this.walker.restoreFromLocalStorage(name)
        this.walker.restorePositions(name)
        setTimeout(() => {
            this.draw()
        }, 300);
    }

    animDraw(){
        this.layerGroup.animDraw()
    }
}


