# NIMAGEN: Statistical and Visualisation tool for NeuroIMAging GENetics studies

See the [example documentation](docs/example/visualisation.rst) for detailed walkthrough of some of the package tools.

## Quick install

1. `pip install lehai-ml/nimagen`
2. `conda install -c lehai-ml nimagen`

Main functions of ```nimagen``` is to 
1. Perform mass linear regression tests and subsequent stability tests.
2. Visualise significant results and plot them on brain maps
3. Visualse gene-set based analyses results

## Cite

If using this package, please cite the following [paper](https://www.nature.com/articles/s41398-023-02413-6)

> Le H, Dimitrakopoulou K, Patel H, Curtis C, Cordero-Grande L, Edwards AD, Hajnal J, Tournier JD, Deprez M, Cullen H. Effect of schizophrenia common variants on infant brain volumes: cross-sectional study in 207 term neonates in developing Human Connectome Project. Transl Psychiatry. 2023 Apr 10;13(1):121. doi: 10.1038/s41398-023-02413-6. PMID: 37037832; PMCID: PMC10085987.

Example of a plot created with ```nimagen```

![Example map of brain regions with accompanying legend](images/brainmaps.png)

Figure 1. Example map of brain regions with accompanying legend

![Example regression multiple-plot](images/example_plot.png)
Figure 2. Example regression multiple-plot
