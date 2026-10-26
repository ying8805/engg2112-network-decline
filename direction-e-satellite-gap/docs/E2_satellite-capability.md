# E2 — Can satellite services actually fill the NSW mobile gaps?

**Evidence checked:** 25 October 2026. This section classifies satellite reach, retail availability, and tested voice capability separately. It does not treat them as interchangeable.

## Finding

Satellite technology can reach beyond a terrestrial footprint, but the evidence supports different claims for different services:

- **Coverage potential:** Telstra says its Starlink Direct-to-Cell messaging is available in most outdoor areas of mainland Australia and Tasmania, subject to an eligible Telstra plan and compatible handset, being outside Telstra terrestrial range, and having a clear sky view. That makes many E1 gap cells *potentially reachable for messaging*. Telstra does not publish a downloadable, location-by-location service polygon that can be overlaid on E1, and the service is intermittent. This is not a guarantee of service at every gap cell.
- **Commercially available, phone-to-satellite:** Telstra Satellite Messaging is a retail service. It supports SMS and selected satellite-optimised apps. It does **not** support voice calls, full internet access, or Triple Zero. Its satellite apps are low-bandwidth and intermittent.
- **Voice validated over LEO broadband:** The Australian Government trialled fixed voice over Starlink at regional and remote trial sites. This validates a voice path over a LEO broadband connection using fixed/customer-premises equipment; it does **not** validate a handset making a native mobile voice call directly to a satellite. The dashboard covers November 2024–July 2025 and the Department reports that Starlink and fixed wireless generally performed well on most technical metrics; its broad analysis found no weather impact on LEO performance. A regulator's summary of that Australian dashboard reports a mean opinion score (MOS) of 4.24/5 for Starlink, within the “users satisfied” band. The direct-to-device distinction remains decisive: the ACCC said in October 2026 that D2D voice services were not then available.
- **Fixed satellite broadband/voice:** Starlink broadband is a commercial, address-qualified product that requires a dish/terminal, power, and a suitable sky view. A fixed voice service or VoIP call can use that connection. It can provide a voice alternative at an eligible premises, but it does not provide mobile coverage along roads or while travelling.

**Answer to E2:** D2D satellite messaging can partially fill the *communication-function* gap for text in suitable outdoor conditions. Current evidence does not show commercial D2D mobile voice filling the E1 gaps. Fixed LEO broadband can support voice at some premises, and voice quality was validated in a controlled field trial, but this is a different access mode and cannot be counted as mobile coverage of people and roads.

## Evidence design

### Three evidence labels

1. **Satellite coverage potential** — an operator or regulator describes a broad satellite footprint, but service at the exact E1 location is not established.
2. **Commercial service** — customers can subscribe/use the service now; record device, plan, location, equipment, and sky-view conditions.
3. **Voice capability validated** — voice calls were measured in a trial or offered as a retail service. Record whether that was fixed voice over broadband or direct-to-device mobile voice.

### Government fixed-voice trial

The Department contracted Scyne Advisory to test services in 50 regional and remote regions. The trial ran from November 2024 to July 2025, using Starlink LEO service and NBN fixed wireless or NBN satellite in parallel. Automated tests ran across the day; calls were attempted in 15-minute blocks. The official page links the interactive dashboard and lists the trial regions and nearest towns. Eight NSW regions are listed in data/e2/nsw_voice_trial_sites.csv.

The Department's September 2025 estimates brief says Starlink and NBN fixed wireless generally performed well on most technical metrics and, in broad terms, the trial analysis found no weather effect on LEO performance, while noting the Department was still considering the full results. The dashboard is the primary source for any chart/table copied into a final report. A secondary government-regulator summary (New Zealand Commerce Commission, citing the Australian dashboard) reports MOS: Starlink 4.24, fixed wireless 4.26, GEO satellite 3.17. Do not report those as results for D2D mobile calls.

### Service comparison

| Service | Commercial status (checked 25 Oct 2026) | SMS / messaging | Voice | Broadband / data | Main conditions and E1 relevance |
|---|---|---|---|---|---|
| Telstra Satellite Messaging (Starlink D2D) | Retail service | Yes: SMS, and selected low-bandwidth satellite apps | No phone calls; no Triple Zero | Limited selected apps; no full internet | Compatible handset/software and Telstra Upfront plan; only beyond Telstra terrestrial range; outdoors/clear sky; intermittent. Potentially useful in many E1 gap locations, but not a voice fix. |
| Starlink fixed broadband with fixed voice/VoIP (including Telstra Satellite Voice where address-qualified) | Retail services; check the address and plan | Not the same as mobile SMS | Yes, fixed/home voice or VoIP over satellite broadband | Yes, broadband | Terminal, power, unobstructed sky view, eligible address. Can support a household's voice/broadband, not a moving handset or road corridor. |
| Australian Government LEOSat voice trial (Starlink fixed access) | Trial completed; not itself a retail plan | Not tested as D2D SMS | Fixed voice calls tested; voice-quality evidence available | LEO broadband was the underlying access | 50 regions, Nov 2024–Jul 2025. NSW trial locations provide local examples, not a statewide coverage certification. |
| Optus–Starlink D2D | Partnership announced; no current Optus retail launch verified in the sources checked | Planned/announced | No D2D voice capability verified | No retail D2D broadband verified | Treat as announced capability/potential until Optus publishes a service launch, eligible-device rules, and coverage conditions. |
| TPG/Vodafone–Lynk D2D | Trial/partnership evidence; no retail launch verified in the sources checked | Direct-to-phone text trial reported | No voice capability verified | No retail D2D broadband verified | Trial success is not commercial availability or a service footprint. |

## Joining E2 to E1

Use outputs/generated/summary.csv to report the E1 no-4G area, modelled population, selected State/Regional road length, and hospital count. Then interpret those numbers through the service matrix rather than drawing a false binary satellite coverage map:

- Label E1 cells **terrestrial 4G map gap** (predicted coverage gap, as at 31 January 2026).
- Label the same cells **D2D messaging potential** only where the broad operator statement and outdoor/sky/device/plan conditions may apply. Do not claim exact per-cell availability.
- Label D2D **voice status: not commercially available / not yet validated** as at the evidence date. The current Telstra service explicitly does not make voice calls; ACCC says D2D voice is not currently available.
- Separately label eligible fixed premises **LEO broadband/fixed-voice option**. Do not apply this to people travelling on roads, and do not infer every premises can order the service from a national footprint claim.
- Report the eight NSW government trial regions as **voice tested at named regional trial sites**, not as every place in those SA2s being covered or as evidence of direct-to-device calls.

The key gap is therefore not simply *satellite versus no satellite*. For E1's no-terrestrial-4G population and roads, today's D2D offering supplies intermittent messaging but not a replacement for ordinary voice calling, emergency calling, or full mobile data. Fixed LEO equipment can provide voice and broadband at some premises, but it requires customer-premises equipment and does not follow the user along roads.

## Limits

- ACCC 4G maps are predicted coverage, have a 31 January 2026 reference date, and predate the standardised mapping approach effective 30 June 2026. They show terrestrial 4G only, not D2D or fixed satellite service.
- Telstra's “most outdoor areas” statement is not an exact NSW polygon. Keep any overlay status as **potential / unverified**, not covered.
- Trial results are fixed-voice platform results, not D2D handset voice, and trial sites were selected outside the NBN fixed-line footprint rather than as a sample of all ACCC 4G gap cells.
- Satellite visibility, terminal installation, service availability by address, and D2D handset eligibility are separate conditions. Do not assume a rooftop dish and a handset D2D service are interchangeable.
- Existing Telstra D2D messaging cannot be used to call or directly text Triple Zero. Emergency-call performance under the future UOMO requires confirmation from the final Act, standards and implementation material.

## Sources

- [Australian Government — Trials of voice services and interactive results dashboard](https://www.infrastructure.gov.au/media-communications/modernising-universal-telecommunications-services/trials-voice-services)
- [Australian Government — September 2025 estimates brief on trial findings](https://www.infrastructure.gov.au/sites/default/files/documents/foi26-145-documents-released.pdf) (see printed pages 189–190)
- [New Zealand Commerce Commission — Copper Services Investigation, final recommendation, paragraphs 3.171–3.174](https://www.comcom.govt.nz/assets/Documents/copper-services-investigation/Copper-Services-Investigation-Final-recommendation-report-21-August-2025.pdf) (secondary summary of the Australian dashboard's MOS)
- [Telstra — Satellite support and eligibility](https://www.telstra.com.au/support/mobiles-devices/satellite-to-mobile)
- [Telstra — Telstra Satellite now available](https://www.telstra.com.au/coverage-networks/mobile-technology/satellite-to-mobile)
- [Optus — Starlink partnership announcement](https://www.optus.com.au/connected/news/together-optus-and-spacex)
- [ACCC — Mobile services inquiry discussion paper, October 2026](https://www.accc.gov.au/system/files/mobile-services-inquiry-discussion-paper-october-2026.pdf?download=y) (D2D state, voice availability, and policy context)
- [TPG Telecom — Media releases](https://www.tpgtelecom.com.au/media_release?page=1&year=All) (Lynk partnership/trial announcements)

