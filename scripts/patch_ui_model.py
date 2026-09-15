from pathlib import Path

main_path = Path(r"D:\Workspaces\codex_work\OpenContent\plugin\main.js")
text = main_path.read_text(encoding="utf-8")

# 1. Update DEFAULTS to include preferredModel
old_defaults = "const DEFAULTS = {viewMode: 'simple', typographyTheme: 'serif', feedingFolders: ['得到大脑','我的知识库/收件箱','收件箱','00_Inbox','Clippings'], python: 'python'"
new_defaults = "const DEFAULTS = {viewMode: 'simple', typographyTheme: 'serif', preferredModel: '', feedingFolders: ['得到大脑','我的知识库/收件箱','收件箱','00_Inbox','Clippings'], python: 'python'"

if old_defaults in text:
    text = text.replace(old_defaults, new_defaults)

# 2. Update Settings.display() to add Model Selection UI
old_settings_hook = "new Setting(root).setName('检查本地环境').setDesc('离线检查 Python、依赖、内核和目录权限；不读取笔记和密钥。')"
new_settings_hook = """    // 大模型与 CLI 自定义选择
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
      );

    new Setting(root).setName('检查本地环境').setDesc('离线检查 Python、依赖、内核和目录权限；不读取笔记和密钥。')"""

if old_settings_hook in text:
    text = text.replace(old_settings_hook, new_settings_hook)

# 3. Update configure() modal to include Model Selection field
old_configure_modal = "const codex=field(root,'Codex 原生可执行文件（可选）',this.settings.codex);"
new_configure_modal = """const codex=field(root,'Codex 原生可执行文件（可选）',this.settings.codex);
      const model=field(root,'自定义大模型 (例如: gpt-5.3-codex-spark / sonnet)',this.settings.preferredModel||'');"""

if old_configure_modal in text:
    text = text.replace(old_configure_modal, new_configure_modal)

old_save_assign = "Object.assign(this.settings,{kernelPath:directory.value.trim(),python:python.value.trim(),codex:codex.value.trim()});"
new_save_assign = "Object.assign(this.settings,{kernelPath:directory.value.trim(),python:python.value.trim(),codex:codex.value.trim(),preferredModel:model.value.trim()});"

if old_save_assign in text:
    text = text.replace(old_save_assign, new_save_assign)

# When activating CLI in configure:
old_health_notice = "modal.close();new Notice(Object.keys(health.providers).length?'连接正常，Agent 已配置。':'连接正常，可无 AI 管理材料与审查。');await this.open();"
new_health_notice = """const activeName = Object.keys(health.providers)[0];
        if (activeName && this.settings.preferredModel) {
          try { await this.api('/providers/activate', { name: activeName, model: this.settings.preferredModel }); } catch(e) {}
        }
        modal.close();new Notice(Object.keys(health.providers).length?'连接正常，已配置 Agent 模型: ' + (this.settings.preferredModel || '默认'):'连接正常，可无 AI 管理材料与审查。');await this.open();"""

if old_health_notice in text:
    text = text.replace(old_health_notice, new_health_notice)

main_path.write_text(text, encoding="utf-8")
print("plugin/main.js successfully patched with UI Model Selection!")
