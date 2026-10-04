# Computer vision for Phase 6: feasibility research

**Status:** research only. Nothing has been built, no video was downloaded and no footage was processed.
**Date:** 2026-10-04
**Context:** CRICINTEL is an internal-preview product built only on Cricsheet ball-by-ball event data. It has no ball-tracking, line/length, shot or fielding data. This note asks whether computer vision (CV) applied to video could add those fields, and whether the results would be good enough to publish as factual statistics.

## How to read the sources

Most direct fetches were blocked by the network egress proxy. arXiv, Semantic Scholar, PMC/NCBI, MDPI, IEEE Xplore, CVF open access, Wikipedia, Crossref, ESPNcricinfo, ICC and the Hawk-Eye site all returned `EGRESS_BLOCKED` or no connection. Only `raw.githubusercontent.com` could be reached.

- **PRIMARY** means I opened the page or file myself.
- **SECONDARY** means the claim comes only from a web-search summary of the page. I did not read the paper. Any numbers given are what the summary attributes to the source, and they need checking against the paper before anyone relies on them.
- **unverified** marks a figure that I could not confirm from any opened source.

Given the network limits, almost every claim below is SECONDARY. A human with normal network access should check the key numbers (marked ⚑) before any decision depends on them.

---

## 1. Ball trajectory from broadcast video

**What exists**

- Single-camera 3D trajectory reconstruction is an established research topic, mostly in baseball and football. Examples are "A Spatiotemporal Approach to Extract the 3D Trajectory of the Baseball from a Single View Video Sequence" (ICME 2004) and "Real-time Localization of a Soccer Ball from a Single Camera" (arXiv:2506.07981, 2025). These methods rely on physics priors such as ballistic motion and known ball size, and on a calibrated or calibratable camera. *(SECONDARY)*
- Football has the most mature broadcast benchmark. SoccerNet-v3D (arXiv:2504.10106, 2025) builds 3D ball-localisation ground truth by triangulating synchronised broadcast replays from different angles, using camera calibration from field lines, and offers a monocular baseline. *(SECONDARY)* The fact that football needed a whole dataset effort just to *create* 3D ground truth from broadcast suggests how hard the problem is.
- A US patent, "Methods and systems to track a moving sports object trajectory in 3D using a single camera" (US 11,615,540), names cricket. It fits a 3D track to 2D detections and refines it with physics, but it assumes a **single stable camera** rather than a cut-edited broadcast. *(SECONDARY)*
- Cricket-specific work: Abbas et al., "Deep-Learning-Based Computer Vision Approach For The Segmentation Of Ball Deliveries And Tracking In Cricket" (arXiv:2211.12009, 2022). It segments delivery shots from broadcast with MobileNet/YOLO and tracks the ball with RetinaNet, all in **2D image space**. *(SECONDARY)* Trajectory accuracy in metres: **unverified / not found**.
- "Automated Wicket-Taking Delivery Segmentation and Weakness Detection in Cricket Videos Using OCR-Guided YOLOv8 and Trajectory Modeling" (arXiv:2510.18405, 2025) reports 99.5% mAP50 for pitch detection and 99.18% mAP50 for ball detection. ⚑ *(SECONDARY)* These are **per-frame detection** scores on the authors' own data. They are not trajectory error in world coordinates, and they are not cross-broadcaster.

**I found no peer-reviewed work that reports metric (cm/mm) 3D trajectory error for cricket balls reconstructed from ordinary broadcast footage.** No accuracy figure exists to quote.

**Comparison with Hawk-Eye**

- Hawk-Eye uses about 6 (search sources say 6–10) fixed, synchronised, calibrated high-speed cameras around the ground and triangulates their views into 3D. Sources describe frame rates of 120 Hz in older systems and around 300–340 fps in current ones. *(SECONDARY; sources vary, and I could not open the official site.)*
- Error: secondary sources say Hawk-Eye used to quote an average of about 3.6 mm and now quotes about 2.2 mm. ⚑ *(SECONDARY: The Conversation, sportskeeda, itsonlycricket. I could not open the Hawk-Eye or ICC primary statement, so treat this as **unverified**.)*
- Hawk-Eye also offers iHawk, which captures 4K 120 fps from an umpire chest or boundary camera. *(SECONDARY; vendor page not opened.)* Even the vendor's lighter product uses a **dedicated, controlled camera**, not the broadcast feed.

**Assessment:** Hawk-Eye has fixed cameras, known calibration, high frame rates and multi-view triangulation. Broadcast video has one moving and zooming camera at 25/50 fps, motion blur and frequent cuts. Those differences make the error of broadcast-derived trajectories at least one to two orders of magnitude worse (my estimate, **unverified**). Broadcast-derived trajectories could give rough *qualitative* shapes, such as "swung late" or "bounced steeply". They cannot give metric data.

## 2. Pitch/bounce point, line and length

- Abbas et al. (arXiv:2211.12009) find the bounce frame by tracking the ball's y-coordinate in the front-on view. They then sort each delivery into **3 coarse bins: full, good length, short**. *(SECONDARY)* Per-class accuracy: **unverified**.
- The IEEE DataPort entry "Front Pitch View Shot Extraction and Ball Tracking in Cricket using Deep-Learning" describes the same kind of pipeline. *(SECONDARY)*
- **Line** (off/middle/leg/wide) is harder than length. It needs the lateral pitch position, so the pitch plane must be calibrated against the camera homography. Broadcast cameras pan and zoom, and the stumps and crease are often the only landmarks visible. I found no paper reporting line accuracy against ground truth. *(Finding: absence, based on SECONDARY searches.)*

**Assessment:** coarse length bins from the standard end-on broadcast camera are research-feasible. A metric pitch point (x, y in metres) and line need per-frame calibration, and no validated broadcast result exists.

## 3. Batter pose and shot classification

**Datasets and results**

| Work | Classes | Data | Reported result | Status |
|---|---|---|---|---|
| CricShot10 / CricShotClassify, Sen et al., *Sensors* 21(8):2846, MDPI 2021 | 10 shots (cover, defence, flick, hook, late cut, lofted, pull, square cut, straight, sweep) | YouTube videos covering Test, ODI and T20 | ~93% (VGG16 fine-tuned variants); 86% (VGG16–GRU) ⚑ | Class list, source and research-only licence: **PRIMARY** (GitHub README). Accuracy: **SECONDARY** |
| Kang, "Modern Deep Learning Approaches for Cricket Shot Classification: A Comprehensive Baseline Study", arXiv:2510.09187, 2025 | (same benchmarks) | Re-implementation study | Standardised re-implementations of earlier claims: 96%→46.0% (LRCN), 99.2%→55.6%, 93%→57.7% (Sensors). Their own EfficientNet-B0+GRU: 92.25% ⚑ | SECONDARY |
| "Building a Video Dataset for Cricket Shot Analysis", IEEE conf., 2023 (doc 10276358) | 4 shot types, balanced | Not opened | **unverified** | SECONDARY |
| UJ-AQA-CricketVision (I3D-AE-LSTM, Univ. Johannesburg) | Stroke *quality*, not type | 8,540 clips; pose keypoints | Spearman ρ ≈ 0.84 ⚑ | SECONDARY |
| Pose-based coaching tools: PoseForge (arXiv:2608.05971), Poze (MotionBERT, 17 joints) | Kinematics | Monocular video | No cricket-specific 3D error found | SECONDARY |
| MediaPipe + Random Forest stroke prediction (UVa thesis) | — | — | "99.77%" ⚑ | SECONDARY; likely a small, single-source dataset |

**Key observations**

1. **Reproducibility.** The 2025 baseline study re-implemented three published cricket shot classifiers under a standard protocol and found them 35–45 points below the accuracy their authors reported *(SECONDARY)*. Headline numbers in this literature should not be trusted without independent re-evaluation.
2. **Datasets are small and single-view.** They use the end-on broadcast camera only, and they consist of pre-trimmed clips chosen as clean examples of each shot. They do not cover every delivery in a match. Cricket shot categories also overlap: a "push" vs a "drive", "lofted" as a modifier rather than a class.
3. **Cross-broadcaster generalisation is not reported** in any work I found. CricShot10 mixes formats but does not report results for each broadcaster or each year.
4. **Pose.** Off-the-shelf 2D pose estimators such as MediaPipe or HRNet run on batters in broadcast frames. In the end-on view the bat and the batter's arms often hide each other, and resolution is low on wide shots. No cricket-specific 3D pose accuracy against motion capture was found (**unverified**).

**Assessment:** classifying a coarse **shot family** (attacking or defensive; off or leg side; along the ground or aerial) from the end-on view is research-feasible. A fine 10-class label for every ball is not reliable enough for statistics.

## 4. Fielder detection and field settings

- IIIT Hyderabad (Prof. Vineet Gandhi's group) built a system that tracks all 11 fielders live and shows their positions on screen. It was used in Asia Cup broadcasts. It uses **one or more static cameras capturing a top view of the whole field**, not the edited broadcast feed. *(SECONDARY; IIIT blog.)*
- Quidich's "Tracker" reports a model trained on about 750k images that tracks players at 25 fps with a 4-frame delay. It is deployed with broadcasters' own camera access. *(SECONDARY; IndiaAI article.)*
- General work on tracking players in broadcast video exists, such as "A Hybrid Approach for Tracking Individual Players in Broadcast Match Videos" (arXiv:2003.03271) and FieldMOT (CVPRW 2025). *(SECONDARY)*

**Assessment:** the edited broadcast seldom shows the whole field at the moment of delivery. The usual end-on shot shows close catchers only, and graphics sometimes replace the wide field view. So **full field-setting reconstruction from broadcast is not feasible**. Partial inference, such as "slips present: 2–3", is plausible. Working systems all depend on dedicated cameras.

## 5. Edge and contact detection

- Snicko and UltraEdge (Hawk-Eye) use a **stump microphone**. Its audio is synchronised with high-frame-rate video and filtered, and an operator, then the third umpire, interprets the result. *(SECONDARY)*
- Academic work: a paper in the *Turkish Journal of Electrical Engineering & Computer Sciences* (vol. 27, iss. 6, 2019) reports snick-type classification (bat, glove, pad) at 98.3% on self-collected data and **85.7% on real match snicks** ⚑. *(SECONDARY)* Other work uses DSP features with neural nets (JSCI, 2013) or XGBoost/RF (SmartCom 2025). *(SECONDARY)*
- **Broadcast-audio feasibility:** the broadcast mix contains commentary, crowd noise and production audio. The stump mic may or may not be in the mix, and its level varies. Broadcast video at 25/50 fps is too slow to align contact frames the way UltraEdge does. DRS edge calls are contested even with the dedicated system.

**Assessment:** edge detection from broadcast is not feasible now as a statistic. It could only be studied as research on dedicated stump-mic feeds that were licensed or self-recorded.

## 6. Problems with camera angles and production

All of the following are documented as preprocessing problems in cricket video work. Sources include the survey "A survey on event detection based video summarization for cricket" and the IIT Kanpur shot and replay detection projects *(SECONDARY)*.

- **Camera changes and cuts.** Each delivery must first be segmented into front-on pitch-view shots, which is a learned step with its own error (Abbas et al. 2022).
- **Zoom and pan.** These break any fixed homography, so calibration has to be redone frame by frame from a few landmarks: stumps, creases and pitch edges.
- **Replays.** Replays are often slow-motion and from another angle. They must be detected (logo-transition heuristics exist) or they double-count deliveries.
- **Overlays.** Score bugs, sponsor graphics and broadcaster ball-tracking graphics hide the ball or pitch.
- **Day/night, shadows, ball colour.** Red, white and pink balls under different lighting.
- **Broadcaster style.** Camera height, lens and end-on position differ by venue and producer. No published cricket model reports results tested across broadcasters.
- **Coverage gaps.** Highlights omit most deliveries. Even full feeds lose deliveries to ad breaks (e.g. strategic timeouts), replays shown over live action and technical faults. **Coverage completeness cannot be assumed**, and a statistic computed on the subset that happens to be visible is biased.

## 7. Labelled training data

- **CricShot10:** 10 classes from YouTube. Access by email request, for **"research purposes only"** *(PRIMARY)*. The underlying footage belongs to broadcasters and rights holders, so a research-only dataset of YouTube clips gives **no rights to commercial use**.
- Other datasets: UJ-AQA-CricketVision (8,540 clips), the IEEE 4-class shot dataset, IEEE DataPort cricket datasets, and the umpire-pose dataset (arXiv:1809.06217). Licence terms are **unverified** for each one *(SECONDARY)*. Accepted practice for YouTube-derived research datasets is to share video IDs and timestamps, not the footage, because the footage stays under its owners' copyright *(SECONDARY)*.
- **No public dataset has calibrated 3D ball ground truth for cricket.** Hawk-Eye data is proprietary.
- **Labelling estimate (my estimate, unverified):**
  - Shot family: a few thousand labelled deliveries per class across several broadcasters, venues and years, with two or more annotators and agreement measured. Roughly 20–50k labelled deliveries for a robust multi-broadcaster set.
  - Trajectory or pitch point: per-frame ball boxes plus calibrated ground truth, which is only achievable with your own calibrated cameras or a Hawk-Eye-type partner.

## 8. Video rights

- Broadcast footage of international cricket is the intellectual property of the ICC and the member boards, licensed exclusively to broadcasters. The ICC's event IPR guidance protects "ICC Footage". It bans ball-by-ball data transmission from venues without permission and gives the ICC the duty to stop unlicensed third parties from activities that "damage or dilute" the exclusive rights of the ICC and its broadcast and commercial partners. *(SECONDARY; ICC PDF and ICC news pages not opened.)* The ICC has also issued takedowns to YouTube for World Cup clips *(SECONDARY)*. Board and league rights such as IPL, The Hundred and BBL belong to the respective boards and their broadcast partners.
- **What would be needed:** a written licence from the rights holder (the board, the ICC or the league) and usually from the host broadcaster. It would have to cover access to the footage, automated processing, storage, and **commercial publication of derived data**. Data rights are often licensed separately from video rights, sometimes exclusively to official data partners.
- **Why scraping or processing without permission is unacceptable:** it reproduces copyrighted footage and breaches platform terms (YouTube ToS prohibit downloading without authorisation). It would probably infringe the rights holders' exclusive data and broadcast licences, and it puts the product at legal and reputational risk. "Research only" licences such as CricShot10's do not carry over to a consumer product. *(I am not a lawyer; this needs legal review. See `docs/legal/`.)*
- **Legitimate alternatives:**
  1. Own-camera footage at amateur, club or academy level, with written consent from players, parents for juniors, and the club. Fixed, calibrated cameras make the problem much easier (iHawk-style).
  2. Partnerships with a board, league or broadcaster, or with an official tracking or data provider (Hawk-Eye, CricViz or an official data partner), to license **derived data** rather than process video at all.
  3. Keep CV purely as internal research on licensed or self-recorded footage, with no published outputs.

## 9. Research prototype vs factual consumer statistics

A research result such as "92% top-1 accuracy on a held-out split" does not meet the bar for publishing facts. In a product built on factual statistics:

- **Errors compound into published claims.** At 90% accuracy, about 1 in 10 shots shown as "pull" is something else. Aggregates like "X plays the pull 23% of the time" carry a systematic bias that depends on the class, and confusion between similar classes is **not** symmetric.
- **Required before any CV-derived field is shown as fact:**
  - per-label precision and recall, plus a confusion matrix, validated on a **held-out, multi-broadcaster, multi-venue, multi-season** test set labelled by expert annotators with measured inter-annotator agreement;
  - **per-prediction confidence**, with an abstain threshold; low-confidence calls are hidden, not guessed;
  - **coverage reporting**, meaning the share of deliveries seen in a usable view and classified, shown alongside every aggregate;
  - **error bars** on aggregates, propagated from the confusion matrix and not just sample size;
  - **auditability**, meaning every number traces back to source frames, model version and confidence, with re-runs reproducible;
  - **drift monitoring** as broadcasters change graphics, cameras or formats.
- The cricket literature currently reports none of the cross-broadcaster validation, calibration or coverage figures above. Its headline accuracies fail independent replication (Kang 2025, SECONDARY). For CRICINTEL, **Cricsheet-grade factual standards cannot currently be met by any CV-derived field**.

## 10. Verdicts

| Capability | Research feasibility | Production-factual | Reason | What would change the verdict |
|---|---|---|---|---|
| **Ball trajectory (3D)** | NOT-FEASIBLE-NOW from broadcast (2D image tracks only are feasible) | **NO** | No published metric-accuracy result from broadcast; one moving camera, 25/50 fps, cuts. Hawk-Eye needs about 6+ calibrated high-speed cameras (SECONDARY) | Own calibrated multi-camera rig, or licensed Hawk-Eye/official tracking data |
| **Pitch/bounce point** | RESEARCH-FEASIBLE (coarse, from end-on view) | **NO** | Bounce frame detectable (Abbas 2022, SECONDARY), but metric position needs per-frame calibration; accuracy unverified | Calibrated fixed camera; validation against Hawk-Eye ground truth |
| **Line / length** | RESEARCH-FEASIBLE for 3-bin length; NOT-FEASIBLE-NOW for line | **NO** (length bins: CONDITIONAL at best) | Only coarse full/good/short shown; no line ground truth found | Licensed footage plus calibration, multi-broadcaster validation, per-bin confidence and coverage reporting |
| **Shot family** | RESEARCH-FEASIBLE (coarse families) | **CONDITIONAL** | Published 10-class accuracies don't replicate (93%→57.7%, SECONDARY); no cross-broadcaster results; class definitions ambiguous | Rights-cleared footage; large multi-broadcaster expert-labelled set; per-label precision/recall plus abstention; coverage shown; coarse families only |
| **Batter pose** | RESEARCH-FEASIBLE (2D); 3D NOT-FEASIBLE-NOW as metric | **NO** for broadcast (coaching use on own footage is another product) | Off-the-shelf 2D pose works; occlusion and low resolution; no cricket 3D validation found | Own high-res fixed cameras with consent; motion-capture validation |
| **Fielder positions** | NOT-FEASIBLE-NOW from broadcast (partial close-catcher inference only) | **NO** | Broadcast rarely shows the whole field; working systems (IIIT-H, Quidich) use dedicated top-view cameras (SECONDARY) | Partnership with a tracking provider or broadcaster; own wide-view camera at amateur level |
| **Edges** | NOT-FEASIBLE-NOW from broadcast audio | **NO** | Needs stump-mic plus high-fps sync; broadcast mix and frame rate unsuitable; even DRS edges contested | Licensed stump-mic feed; or remain official-DRS-only data from a partner |

**Overall recommendation:** do **not** start a Phase 6 that processes broadcast video. If CV is pursued, the two candidates are:

- an internal research spike on **self-recorded, consented amateur footage** with a fixed calibrated camera (length bins, coarse shot family, 2D pose);
- a **data-licensing conversation** with an official tracking or data provider.

Any CV-derived field would need to be labelled as an *estimate*, kept separate from Cricsheet facts, and shipped with confidence and coverage figures.

---

## Sources

Status in brackets. **PRIMARY** = opened. **SECONDARY** = search summary only.

1. Sen, Deb, Dhar, Koshiba. "CricShotClassify: An Approach to Classifying Batting Shots from Cricket Videos Using a CNN and GRU." *Sensors* 21(8):2846, MDPI, 2021. https://www.mdpi.com/1424-8220/21/8/2846 · https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8072636/ [SECONDARY]
2. CricShot10 dataset README (classes, YouTube source, research-only access). https://github.com/ascuet/CricShot10 (fetched via raw.githubusercontent.com) [PRIMARY]
3. Kang, S. "Modern Deep Learning Approaches for Cricket Shot Classification: A Comprehensive Baseline Study." arXiv:2510.09187, 2025. https://arxiv.org/abs/2510.09187 [SECONDARY]
4. Abbas, Saeed, Khan, Ahmed, Wang. "Deep-Learning-Based Computer Vision Approach For The Segmentation Of Ball Deliveries And Tracking In Cricket." arXiv:2211.12009, 2022. https://arxiv.org/abs/2211.12009 [SECONDARY]
5. "Automated Wicket-Taking Delivery Segmentation and Weakness Detection in Cricket Videos Using OCR-Guided YOLOv8 and Trajectory Modeling." arXiv:2510.18405, 2025. https://arxiv.org/abs/2510.18405 [SECONDARY]
6. "Front Pitch View Shot Extraction and Ball Tracking in Cricket using Deep-Learning." IEEE DataPort. https://ieee-dataport.org/documents/front-pitch-view-shot-extraction-and-ball-tracking-cricket-using-deep-learning [SECONDARY]
7. "Building a Video Dataset for Cricket Shot Analysis." IEEE conference, 2023. https://ieeexplore.ieee.org/document/10276358 [SECONDARY]
8. "I3D-AE-LSTM: a 2-stream autoencoder for action quality assessment" (UJ-AQA-CricketVision). Univ. of Johannesburg. https://pure.uj.ac.za/en/publications/i3d-ae-lstm-a-2-stream-autoencoder-for-action-quality-assessment- [SECONDARY]
9. "PoseForge: Editable Pose Analytics for AI-Assisted Sports Coaching." arXiv:2608.05971. https://arxiv.org/abs/2608.05971 [SECONDARY]
10. "Enhancing Cricket Performance Analysis" (MediaPipe + ML stroke prediction). Univ. of Valladolid. https://uvadoc.uva.es/bitstream/handle/10324/66573/Enhancing-Cricket-Performance-Analysis.pdf [SECONDARY]
11. "A Spatiotemporal Approach to Extract the 3D Trajectory of the Baseball from a Single View Video Sequence." ICME 2004. https://www.hubertshum.com/pbl_icme2004ball.htm [SECONDARY]
12. "Real-time Localization of a Soccer Ball from a Single Camera." arXiv:2506.07981, 2025. https://arxiv.org/abs/2506.07981 [SECONDARY]
13. "SoccerNet-v3D: Leveraging Sports Broadcast Replays for 3D Scene Understanding." arXiv:2504.10106, 2025. https://arxiv.org/abs/2504.10106 [SECONDARY]
14. US Patent 11,615,540. "Methods and systems to track a moving sports object trajectory in 3D using a single camera." https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11615540 [SECONDARY]
15. Hawk-Eye Innovations: officiating/SMART, TRACK, iHawk pages. https://www.hawkeyeinnovations.com/officiating · https://www.hawkeyeinnovations.com/ihawk [SECONDARY; direct fetch blocked]
16. "Out! Goal! The ball was in! But could Hawk-Eye get it wrong?" *The Conversation*. https://theconversation.com/out-goal-the-ball-was-in-but-could-hawk-eye-get-it-wrong-20741 [SECONDARY]
17. "Hawk-Eye Technology: How Does Cricket Ball Tracking Work?" itsonlycricket. https://www.itsonlycricket.com/cricket-ball-tracking [SECONDARY]
18. Sportskeeda, "The DRS conundrum" (2.2 mm error window). https://www.sportskeeda.com/cricket/drs-bcci-right-about-decison-review-system-after-all/4 [SECONDARY]
19. Wisden, "Explained: what is the Smart Replay System in IPL 2024." https://www.wisden.com/series/tata-indian-premier-league-2023-24/cricket-news/explained-what-is-the-smart-replay-system-in-ipl-2024 [SECONDARY]
20. Snick classification from audio. *Turkish J. Electrical Eng. & Comp. Sci.* 27(6), 2019. https://journals.tubitak.gov.tr/elektrik/vol27/iss6/7 [SECONDARY]
21. Edge detection with DSP and neural networks. *J. Systemics, Cybernetics and Informatics*, 2013. https://doaj.org/article/e5864174fa1a4fc69bdd62f7aa6bee20 [SECONDARY]
22. IIIT Hyderabad, "IIITH's Player Tracking Tech Drives Asia Cup's Narrative For Viewers." https://blogs.iiit.ac.in/player-tracking/ [SECONDARY]
23. IndiaAI, "How Quidich Innovation Labs use AI for real-time player tracking for cricket." https://indiaai.gov.in/article/how-quidich-innovation-labs-use-ai-for-real-time-player-tracking-for-cricket [SECONDARY]
24. "A Hybrid Approach for Tracking Individual Players in Broadcast Match Videos." arXiv:2003.03271. https://arxiv.org/abs/2003.03271 [SECONDARY]
25. "A survey on event detection based video summarization for cricket." (ResearchGate copy) https://researchgate.net/publication/359692483 [SECONDARY]
26. ICC event IPR / media guidelines (PDF). https://images.icc-cricket.com/image/upload/prd/xrsvd5txbzwevupq4bmh.pdf ; ICC, "ICC to begin legal proceedings against infringing news channels." https://icc-cricket.com/news/icc-to-begin-legal-proceedings-against-infringing-news-channels [SECONDARY]
27. IPKat, "Cricket; academic settled copyright case" (ICC takedowns context). https://ipkitten.blogspot.com/2007/03/cricket-academic-settled-copyright-case.html [SECONDARY]
28. "A Dataset and Preliminary Results for Umpire Pose Detection Using SVM Classification of Deep Features." arXiv:1809.06217. https://arxiv.org/abs/1809.06217 [SECONDARY]

**Tally:** 1 PRIMARY, 27 SECONDARY (28 source entries).
