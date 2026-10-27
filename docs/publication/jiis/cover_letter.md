27 October 2026

Prof. Zbigniew Ras
Editor-in-Chief, Journal of Intelligent Information Systems

Dear Prof. Ras,

We submit our manuscript, "What Does Flattening Hide? Measuring Case-Notion Distortion and Its Consequences on Seven Real Object-Centric Event Logs", for consideration as a research article in the Journal of Intelligent Information Systems.

Information systems record events that relate to several objects at once, but process-mining tools still expect one case per event. Analysts therefore flatten the extracted event data on one object type. The journal has published work on extracting object-centric event data from ERP databases (Berti et al., 2023). Our paper looks at the step that follows extraction: what is lost when such data is flattened for a case-centric tool. The literature names the problems (convergence, divergence, deficiency), but we found no study that measures them across several real logs.

We measured them on seven public object-centric logs from code review, education, legislation, e-mail, blockchain, software commits and game play, covering 38 case notions, and compared five outputs an analyst reads (activity rankings, directly-follows edges, variants, entity rankings and a discovered process model) between flat and object-centric views. The logs fall into three regimes. Duplication rarely changes a ranking. Narrowing is common: much of it is structural, but it persists in reasonable case notions, and in two logs no case notion covers half of the events. Discovered models do not reveal it, because every narrowed case notion still yields a replay fitness of at least 0.955. Counting rows in a denormalised export can reverse entity rankings. All headline numbers carry bootstrap intervals, and we report the sensitivity of the counts to every threshold we chose.

The contribution is empirical, and the paper is open about its limits: seven logs chosen for variety rather than at random, thresholds chosen by us, and three of the 38 case notions that our process-discovery setup could not mine. A second implementation reproduces the distortion metrics exactly on all seven full logs. All data is public and openly licensed, no synthetic data was used, and personal identifiers are hashed. The code regenerates every number with one command; it is openly available at https://github.com/ssaakaash/ocel-research.

The manuscript is original, has not been published, and is not under consideration elsewhere. All authors have approved it. The use of generative AI is documented in Section 3.7.

Sincerely,
Dr. Kalyanaraman P. (corresponding author)
School of Computer Science and Engineering, Vellore Institute of Technology, Vellore 632014, India
pkalyanaraman@vit.ac.in
On behalf of all authors
