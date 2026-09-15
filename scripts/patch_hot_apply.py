from pathlib import Path

main_path = Path(r"D:\Workspaces\codex_work\OpenContent\plugin\main.js")
text = main_path.read_text(encoding="utf-8")

# 1. Look for the configure modal button handler
old_btn_logic = """      button(root,'保存并检查连接',async()=>{
        if(this.connection)throw new Error('当前已连接。更改运行环境前，请先停用并重新启用插件。');
        Object.assign(this.settings,{kernelPath:directory.value.trim(),python:python.value.trim(),codex:codex.value.trim(),preferredModel:modelSelect.value});
        await this.saveData(this.settings);await this.startKernel();const health=await this.api('/health');
        const activeName = Object.keys(health.providers)[0];
        if (activeName && this.settings.preferredModel) {
          try { await this.api('/providers/activate', { name: activeName, model: this.settings.preferredModel }); } catch(e) {}
        }
        modal.close();new Notice(Object.keys(health.providers).length?'连接正常，已配置 Agent 模型: ' + (this.settings.preferredModel || '默认'):'连接正常，可无 AI 管理材料与审查。');await this.open();
      },'mod-cta');"""

new_btn_logic = """      button(root,'保存并检查连接',async()=>{
        const newKernel = directory.value.trim();
        const newPython = python.value.trim();
        const newCodex = codex.value.trim();
        const newModel = modelSelect.value;
        const kernelChanged = newKernel !== this.settings.kernelPath || newPython !== this.settings.python || newCodex !== this.settings.codex;

        Object.assign(this.settings, {
          kernelPath: newKernel,
          python: newPython,
          codex: newCodex,
          preferredModel: newModel
        });
        await this.saveData(this.settings);

        if (this.connection) {
          // If only model or non-kernel settings changed, hot-apply directly
          if (!kernelChanged) {
            try {
              const providers = await this.api('/providers');
              const activeName = Object.keys(providers.active)[0];
              if (activeName) {
                await this.api('/providers/activate', { name: activeName, model: newModel });
              }
              modal.close();
              new Notice('已应用设置！当前模型: ' + (newModel || '系统默认'));
              await this.open();
              return;
            } catch(e) {}
          }
          // If kernel path or python changed, perform graceful hot restart
          try {
            await this.api('/shutdown', {});
          } catch(e) {}
          this.connection = null;
          if (this.child) {
            try { this.child.kill(); } catch(e) {}
            this.child = null;
          }
          await new Promise(r => setTimeout(r, 600));
        }

        await this.startKernel();
        const health = await this.api('/health');
        const activeName = Object.keys(health.providers)[0];
        if (activeName && this.settings.preferredModel) {
          try { await this.api('/providers/activate', { name: activeName, model: this.settings.preferredModel }); } catch(e) {}
        }
        modal.close();
        new Notice(Object.keys(health.providers).length ? '已连接，当前模型: ' + (this.settings.preferredModel || '系统默认') : '连接正常，可无 AI 管理材料与审查。');
        await this.open();
      },'mod-cta');"""

if old_btn_logic in text:
    text = text.replace(old_btn_logic, new_btn_logic)
    main_path.write_text(text, encoding="utf-8")
    print("Successfully replaced rigid throw with seamless hot-apply / hot-restart!")
else:
    print("Target block not matched exactly, checking diff...")
