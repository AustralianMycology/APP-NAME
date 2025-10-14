import os, glob, subprocess, yaml, pathlib
OPENAI_KEY=os.getenv("OPENAI_API_KEY","")
MODEL=os.getenv("OPENAI_MODEL","gpt-5.1-mini")
TASK_GLOB=os.getenv("GPT2_TASK_GLOB","gpt2/tasks/*.yaml")
TARGET_BRANCH=os.getenv("GPT2_BRANCH","gpt2/setup")
PROMPT="You are an automated implementation unit. Return ONLY a unified git diff from repo root."

def run(cmd, check=True):
    return subprocess.run(cmd, check=check, text=True, capture_output=True)

def ask_llm(prompt:str)->str:
    if not OPENAI_KEY: return ""
    import openai; openai.api_key=OPENAI_KEY
    r=openai.ChatCompletion.create(
        model=MODEL,
        messages=[{"role":"system","content":"You produce only patches."},
                  {"role":"user","content":prompt}],
        temperature=0.2,
    )
    return r.choices[0].message["content"]

def apply_patch(patch:str)->bool:
    if not patch.strip(): return False
    pathlib.Path("gpt2/out").mkdir(parents=True, exist_ok=True)
    pf="gpt2/out/patch.diff"; pathlib.Path(pf).write_text(patch, encoding="utf-8")
    try:
        run(["git","apply","--reject","--whitespace=fix",pf]); return True
    except subprocess.CalledProcessError:
        return False

def main():
    run(["git","checkout","-B",TARGET_BRANCH])
    files = run(["git","ls-files"], check=False).stdout.splitlines()
    repo_tree = "\n".join(files)[:4000]
    tasks = sorted(glob.glob(TASK_GLOB))
    if not tasks:
        print("No tasks."); return
    for t in tasks:
        task = yaml.safe_load(open(t, encoding="utf-8"))
        prompt = f"Repo tree:\n{repo_tree}\n\nTask YAML:\n{yaml.safe_dump(task)}\n\n{PROMPT}"
        patch = ask_llm(prompt)
        if not apply_patch(patch): continue
        try: run(["bash","scripts/ci.sh"])
        except subprocess.CalledProcessError:
            run(["git","reset","--hard","HEAD"]); continue
        run(["git","add","-A"])
        if run(["git","status","--porcelain"], check=False).stdout.strip():
            run(["git","-c","user.name=gpt2-bot","-c","user.email=bot@users.noreply.github.com",
                 "commit","-m",f"chore(gpt2): {task.get('id','task')} - {task.get('goal','')}"])
            try: run(["git","push","-u","origin",TARGET_BRANCH])
            except subprocess.CalledProcessError:
                pass

if __name__=="__main__": main()
