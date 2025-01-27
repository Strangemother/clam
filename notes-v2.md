In the first draft, I successfully bridged multiple models through one (flask) interface.

It was limited owning to a pure HTTP base. This needs to change to a pure websocket solution. Luckily, I enjoy websockets.

+ [Porthouse](https://github.com/Strangemother/python-porthouse)

---

+ The JAN UI is openai compatible (Cortex Fast API).
+ Msty UI is olloma
+ Pinkokio endpoints are Gradio

---

Therefore we create a websocket solution connecting them. With a central mesh merging them. Luckily Porthouse does this.


## Reading Resources

Gradio has a _definition_ used to create the UI. This includes endpoints and expected resources. a `gradio-client` exists, but for some reason this doesn't function for me. However it seems possible to mostly wrap it.

Olloma is great. Simple endpoints e.g. `api/tags/` provide JSON responses. The data response is websocket events.

Cortext (openai compatible) seems to be a reduced version of the openai api. but the `openai` client doesn't function for me `jiter DLL issue`.


