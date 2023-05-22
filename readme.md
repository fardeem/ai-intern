# ai-intern

A full project generation tool using gpt-4. Make new projects and edit old projects, leveraging your very own ai-intern.



## running

```bash
pip install modal-client
modal token new

modal run main.py --prompt flask.md
```

To run on any directory, copy and edit `run.sh.sample` and rename to `run.sh`. Then,

```bash
sudo ln -s <directory>/ai-intern/run.sh /usr/local/bin/ai-intern
```

Then run,

```bash
ai-intern --prompt "my next best website"
```



## notes

if you don't set a `concurrency_limit` on calling the api you get rate limited by openai. It works with

- `n = 10` for the flask prompt and takes 2 mins, 
- `n = 5` and takes ~4 mins
- `n = 20` also took ~2 mins so I think at that point open ai's API becomes the rate limiting factor

## inspiration

[swyx's smol developer](https://github.com/smol-ai/developer/)

[english compiler](https://github.com/uilicious/english-compiler)