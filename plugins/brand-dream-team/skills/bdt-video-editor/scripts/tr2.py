import sherpa_onnx, soundfile as sf, json, sys
d=sys.argv[1]
r=sherpa_onnx.OfflineRecognizer.from_transducer(encoder=d+"/encoder-epoch-99-avg-1.int8.onnx",decoder=d+"/decoder-epoch-99-avg-1.onnx",joiner=d+"/joiner-epoch-99-avg-1.int8.onnx",tokens=d+"/tokens.txt",num_threads=4)
a,sr=sf.read(sys.argv[2],dtype="float32")
words=[];CH=15
for off in range(0,len(a),CH*sr):
    st=r.create_stream(); st.accept_waveform(sr,a[off:off+CH*sr]); r.decode_stream(st)
    res=st.result; base=off/sr
    for t,ts in zip(res.tokens,res.timestamps):
        if t.startswith(("▁"," ")) or not words or words[-1].get("closed"):
            words.append({"w":t.replace("▁","").strip(),"s":round(base+ts,2)})
        else: words[-1]["w"]+=t
    if words: words[-1]["closed"]=True
for i,w in enumerate(words):
    w.pop("closed",None); w["e"]=round(min(w["s"]+0.6, words[i+1]["s"] if i+1<len(words) else w["s"]+0.5),2)
json.dump(words,open(sys.argv[3],"w"))
print(" ".join(f"{x['w'].lower()}[{x['s']}]" for x in words))
