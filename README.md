# TTS

## Performance

High-throughput speech synthesis is mostly about respecting the shared rate
limits while keeping disks and CPUs busy. The CLI exposes a
`--concurrency` flag that now defaults to **2**, which balances throughput
and stability for the public service tier. Raising concurrency to **5-6** can
speed up large batches, but the trade-off is a much higher chance of HTTP 429
throttling. When you approach those values, monitor the logs closely; the tool
will clamp anything above **6** and warn you when you sail close to the limits.
If you regularly need to push beyond what the shared API can handle, use Azure
Batch to stage your jobs where the platform can scale with you.

Rate limiting also interacts with your audio settings. Each request includes a
crossfade buffer that defaults to 120ms. If you notice disks struggling to keep
up—particularly on networked storage—reduce `--crossfade` toward 40-60ms. This
shrinks the per-request payload and keeps IO queues from backing up while only
slightly affecting clip blending quality.

Finally, mind your disk layout. Batched synthesis produces many short-lived
files, so put your working directory on SSD-backed storage and avoid sharing it
with other heavy workloads. This keeps write amplification low and ensures the
CPU is not waiting on IO when the network has headroom.
