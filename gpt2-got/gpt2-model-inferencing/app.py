from starlette.applications import Starlette
from starlette.responses import UJSONResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
import gpt_2_simple as gpt2
import tensorflow as tf
import uvicorn
import os
import gc
import time


middleware = [
  Middleware(CORSMiddleware, allow_origins=['*'], allow_headers=['*'], expose_headers=['Access-Control-Allow-Origin']),
]

app = Starlette(middleware=middleware, debug=False)

sess = gpt2.start_tf_sess(threads=1)
gpt2.load_gpt2(sess)

# Needed to avoid cross-domain issues
response_header = {
    'Access-Control-Allow-Origin': '*'
}

generate_count = 0

print("-------------------")
print("Num GPUs Available: ", len(tf.config.experimental.list_physical_devices('GPU')))
print("-------------------")


@app.route('/', methods=['GET', 'POST', 'HEAD'])
async def homepage(request):
    global generate_count
    global sess

    start = time.time()



    if request.method == 'GET':
        params = request.query_params
    elif request.method == 'POST':
        params = await request.json()
    elif request.method == 'HEAD':
        return UJSONResponse({'text': ''},
                             headers=response_header)

    text = gpt2.generate(sess,
                         length=int(params.get('length', 1023)),
                         temperature=float(params.get('temperature', 0.7)),
                         top_k=int(params.get('top_k', 0)),
                         top_p=float(params.get('top_p', 0)),
                         prefix=params.get('prefix', '')[:500],
                         truncate=params.get('truncate', None),
                         include_prefix=str(params.get(
                             'include_prefix', True)).lower() == 'true',
                         return_as_list=True
                         )[0]

    generate_count += 1
    if generate_count == 8:
        # Reload model to prevent Graph/Session from going OOM
        tf.reset_default_graph()
        sess.close()
        sess = gpt2.start_tf_sess(threads=1)
        gpt2.load_gpt2(sess)
        generate_count = 0

    gc.collect()

    end = time.time()
    elapsed_time = end - start
    print(f"The request took: "+ str(elapsed_time))
    
    return UJSONResponse({'text': text},
                         headers=response_header)

if __name__ == '__main__':
    #uvicorn.run(app, host='0.0.0.0', port=int(8081))
    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))