# Figure brief

## Purpose
Generic KV offload mechanism for one request, one attention layer and one decode step; not a specific vLLM/Ascend commit. Prefill KV is already available. No MTP, graph capture, TP communication or sampling is shown.

## Main path
Query → select KV IDs → resolve KV → attention output. The local expansion shows residency lookup, resident-hit reuse, missing-KV fetch/onload, a readiness join and gathering selected KV for attention.

## Important boundaries
A residency miss requires data transfer before attention consumes the KV. Readiness covers hits and completed miss copies. Selection and residency are separate concepts. This is conceptual data dependency, not a prescribed kernel order; a real implementation may overlap gather and transfer with valid synchronization. CPU destination/source and cache indexing policies are not implementation claims.

## Caption
The main decode path expands residency resolution: cache hits reuse resident KV while misses onload KV; consumption waits for required data to be ready.
