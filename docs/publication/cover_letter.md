[Date]

To the Editors of [journal name]

Dear Editors,

We submit our manuscript, "What Does Flattening Hide? Measuring Case-Notion Distortion and Its Consequences on Seven Real Object-Centric Event Logs", for consideration as a [research article / short paper].

Process mining usually assigns each event to one case, so analysts flatten multi-entity logs by choosing one object type as the case. The literature names the damage (convergence, divergence, deficiency), but we found no study that measures it across several real logs. We measured it on seven public object-centric logs from code review, education, legislation, e-mail, blockchain, software commits and game play, covering 38 case notions. We then compared four outputs an analyst would read (activity rankings, directly-follows edges, process variants and entity rankings) between flat and object-centric views.

Our main findings are these. The logs fall into three groups: star logs where flattening copies nothing, partitioned logs where one case notion drops 69% to 91% of the events in the median, and fan-out logs where events are duplicated, up to 81.65 copies in one log. Duplication alone rarely changes a ranking. The larger effect is narrowing, where the flat log shows fewer than half of the process's activities. Much of it is structural, but it remains in 2 of the 15 case notions that cover at least half of their log, and in two logs no case notion covers half the events. Counting rows in a denormalised flat export can also reverse an entity ranking.

We believe the manuscript fits [journal name] because [one sentence about the journal's scope, for example its coverage of process mining and object-centric data]. We do not claim to be the first to use object-centric logs in education, and we make no claim about any capstone portal, because we had no portal data. The limits are stated in the paper: seven logs chosen for variety rather than at random, thresholds chosen by us (with sensitivity reported), a second implementation of the distortion metrics that covers slices and not the full logs, and no independent labelling of the findings.

The manuscript is original, has not been published, and is not under consideration elsewhere. All authors have approved it. All seven datasets are public and openly licensed, no synthetic data was used, and personal identifiers in two logs were hashed. Code and results are available at [repository DOI]. [Statement on the use of generative AI, matching the one in the manuscript.]

We suggest the following reviewers, none of whom has worked with us: [name, affiliation, e-mail] ... [3 to 5 names]. [Optional: reviewers to exclude.]

Sincerely,
[Corresponding author name, affiliation, e-mail]
On behalf of Aakaash Sathya Saravanan, Mitisha Sharma and Tanmay Khambete
