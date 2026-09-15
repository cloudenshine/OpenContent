from pathlib import Path

main_path = Path(r"D:\Workspaces\codex_work\OpenContent\plugin\main.js")
text = main_path.read_text(encoding="utf-8")

# Replace the text-based Setting in Settings.display() with an intelligent dropdown
old_setting_code = """    // 大模型与 CLI 自定义选择
    new Setting(root)
      .setName('自定义大模型 (Model ID / Override)')
      .setDesc('覆盖 Codex 或 Claude 默认模型。例如 Codex: gpt-5.3-codex-spark, o3-mini, gpt-4o；Claude: claude-3-7-sonnet-latest, opus, sonnet 等。留空使用工具默认值。')
      .addText(t => t
        .setPlaceholder('例如：gpt-5.3-codex-spark 或 claude-3-7-sonnet-latest')
        .setValue(this.plugin.settings.preferredModel || '')
        .onChange(async v => {
          this.plugin.settings.preferredModel = v.trim();
          await this.plugin.saveData(this.plugin.settings);
          if (this.plugin.connection) {
            try {
              const providers = await this.plugin.api('/providers');
              const activeName = Object.keys(providers.active)[0];
              if (activeName) {
                await this.plugin.api('/providers/activate', { name: activeName, model: this.plugin.settings.preferredModel });
                new Notice('已将模型切换为: ' + (this.plugin.settings.preferredModel || '默认'));
              }
            } catch(e) {}
          }
        })
      );"""

new_setting_code = """    // 从本地 Codex / Claude 智能发现的大模型下拉选择菜单
    const modelSetting = new Setting(root)
      .setName('选择大模型 (AI Model Selection)')
      .setDesc('自动检测本地 Codex / Claude 账户拥有的全部大模型列表。');

    (async () => {
      let modelsList = [];
      try {
        if (this.plugin.connection) {
          const res = await this.plugin.api('/models');
          modelsList = res.models || [];
        }
      } catch(e) {}

      if (!modelsList.length) {
        // Fallback common models
        modelsList = [
          { id: '', name: '⚡ 使用系统默认模型 (System Default)' },
          { id: 'gpt-5.3-codex-spark', name: 'gpt-5.3-codex-spark (极速)' },
          { id: 'gpt-5.6-sol', name: 'gpt-5.6-sol (旗舰高智)' },
          { id: 'gpt-5.6-terra', name: 'gpt-5.6-terra (平衡)' },
          { id: 'gpt-5.6-luna', name: 'gpt-5.6-luna' },
          { id: 'gpt-5.4-mini', name: 'gpt-5.4-mini' },
          { id: 'claude-3-7-sonnet-latest', name: 'Claude 3.7 Sonnet' },
          { id: 'claude-3-5-sonnet-latest', name: 'Claude 3.5 Sonnet' },
          { id: 'o3-mini', name: 'o3-mini' }
        ];
      } else {
        modelsList.unshift({ id: '', name: '⚡ 使用系统默认模型 (System Default)' });
      }

      modelSetting.addDropdown(dd => {
        for (const m of modelsList) {
          dd.addOption(m.id, m.name || m.id);
        }
        dd.setValue(this.plugin.settings.preferredModel || '');
        dd.onChange(async v => {
          this.plugin.settings.preferredModel = v;
          await this.plugin.saveData(this.plugin.settings);
          if (this.plugin.connection) {
            try {
              const providers = await this.plugin.api('/providers');
              const activeName = Object.keys(providers.active)[0];
              if (activeName) {
                await this.plugin.api('/providers/activate', { name: activeName, model: v });
                new Notice('已将模型切换为: ' + (v || '系统默认'));
              }
            } catch(e) {}
          }
        });
      });
    })();"""

if old_setting_code in text:
    text = text.replace(old_setting_code, new_setting_code)
    print("Settings dropdown replaced!")
else:
    print("old_setting_code not found")

# Replace in configure() modal as well
old_configure_modal = """const codex=field(root,'Codex 原生可执行文件（可选）',this.settings.codex);
      const model=field(root,'自定义大模型 (例如: gpt-5.3-codex-spark / sonnet)',this.settings.preferredModel||'');"""

new_configure_modal = """const codex=field(root,'Codex 原生可执行文件（可选）',this.settings.codex);
      el(root, 'label', '选择使用的大模型');
      const modelSelect = el(root, 'select');
      modelSelect.setAttribute('aria-label', '选择大模型');
      const defOpt = el(modelSelect, 'option', '⚡ 使用系统默认模型 (System Default)');
      defOpt.value = '';

      (async () => {
        try {
          if (this.connection) {
            const res = await this.api('/models');
            for (const m of (res.models || [])) {
              const opt = el(modelSelect, 'option', m.name || m.id);
              opt.value = m.id;
              if (m.id === this.settings.preferredModel) opt.selected = true;
            }
          }
        } catch(e) {}
      })();"""

if old_configure_modal in text:
    text = text.replace(old_configure_modal, new_configure_modal)
    print("Configure modal dropdown replaced!")
else:
    print("old_configure_modal not found")

old_save_modal = "Object.assign(this.settings,{kernelPath:directory.value.trim(),python:python.value.trim(),codex:codex.value.trim(),preferredModel:model.value.trim()});"
new_save_modal = "Object.assign(this.settings,{kernelPath:directory.value.trim(),python:python.value.trim(),codex:codex.value.trim(),preferredModel:modelSelect.value});"

if old_save_modal in text:
    text = text.replace(old_save_modal, new_save_modal)

main_path.write_text(text, encoding="utf-8")
print("plugin/main.js successfully updated with dynamic model dropdown!")
