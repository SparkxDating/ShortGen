# video-engine

`MoneyPrinterTurboGenerationAdapter` is the only generation entry point used by the SaaS worker.

It calls existing functions in `app/services/task.py`:

- `generate_script`
- `generate_terms`
- `generate_audio`
- `generate_subtitle`
- `get_video_materials`
- `generate_final_videos`

Do not add a second renderer here.
