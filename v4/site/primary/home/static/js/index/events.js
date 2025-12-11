/* Generate events can emit from anywhere.

Two types of _event_ exist for ease

    SystemMessage.emit(Object.assign(action, {
        routing: 'command'
        , _meta: Math.random().toString(32)
        , from: ev
        , callback
    }))

    UserMessage.emit({
        message: target.textContent
        , _meta: Math.random().toString(32)
        , from: ev
    })
*/

class EventCenter {

    constructor(root=window) {
        this._root = root;
    }

    getRoot() {
        return this._root
    }

    static getRoot() {
        return this._root
    }

    reDispatch(type, ev) {
        const newEvent = new ev.constructor(type, ev.type, ev)
        this.dispatch(ev)
        return newEvent
    }

    dispatch(ev) {
        this.getRoot().dispatchEvent(ev)
    }


    emit(name, data, fromEvent) {
        if(data == undefined) {
            data = name;
            name = undefined;
        }

        if(name == undefined) {
            name = fromEvent.getName()
        }

        let cev = new fromEvent(name, {
            detail: data
        })

        cev.getRoot().dispatchEvent(cev)
        return cev;
    }

}

const eventCenter = new EventCenter(window)


class EventBase extends CustomEvent {

    static getName() {
        return this.name
    }

    static center() {
        return eventCenter;
    }

    static emit(name, data) {
        this.center().emit(name, data, this)
    }

    center() {
        return eventCenter;
    }

    getRoot() {
        return eventCenter.getRoot()
    }

    static getRoot() {
        return eventCenter.getRoot()
    }

    static listen(func) {
        /*
            ExampleEvent.listen((e)=>{ console.log('receive', e) });
         */
        this.center().getRoot().addEventListener(this.getName(), func)
    }

    static unlisten(func) {
        /*
            ExampleEvent.unlisten((e)=>{ console.log('receive', e) });
         */
        return this.getRoot().removeEventListener(this.getName(), func)
    }
}


class ExampleEvent extends EventBase {
    /* ExampleEvent.emit({ foo: 1}) */
}


class UserMessage extends EventBase {
    /*
        UserMessage.emit({ foo: 1})
        UserMessage.listen(func)

    in a class:

        UserMessage.listen(this.func.bind(this))
    */
}


class SystemMessage extends EventBase {}


class SetFirstFocusEvent extends EventBase {}
