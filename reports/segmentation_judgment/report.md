# Segmentation QC Criteria

## Notice

1. **When assessing the final Mesh quality, you have two options: LVepi + LVendo, and LVmyo, either one is acceptable, that works.**
<br>
***Recommendation: for the LVepi + LVendo mesh, reject (strict); for the LVmyo mesh, accept***
<br>
    ![](imgs/eg1.1_2.png){width=100}![](imgs/eg1.2.png){width=100}

*(In this case, LVepi + LVendo shows thicker apex than normal heart, while LVmyo looks good, so finally accept this case)*

2. **In some cases, if the overestimation of apical thickness is the only issue, then exclude it from assessment.**
<br>
***Recommendation: under the minimum-requirement standard, accept***
<br>
    ![](imgs/eg2.1_3.png){width=100}![](imgs/eg2.3_2.png){width=95}

*(In this case, due to focal basal hypertrophy, LVmyo is not real and suitable. For LVepi + LVendo, accept the case with excluding the thick apex from assessment)*

3. **Based on observation, LVmyo is not suitable for cases with myocardial hypertrophy, so in these cases, better use LVepi + LVendo for assessment. Also, set the segmentation opacity into 90% to easily identify myocardial hypertrophy.**
<br>
***Recommendation: reject***
<br>
    ![](imgs/eg3.1.png){width=90}![](imgs/eg3.2.png){width=100}

*(In this case, due to diffuse concentric hypertrophy, LVmyo is not real and suitable)*

## Slice misalignment

*Set the segmentation opacity into 90% to observe the LV epicardium and endocardium.*

#### Basal endocardial misalignment

***Recommendation: reject***

![](imgs/Fig4.1.png){width=100}![](imgs/Fig4.2.png){width=100}

*(In this case, no obvious misalignment is observed when assessing the epicardium only, but together with the endocardium, misalignment of the basal endocardium results in an unusual basal morphology)*

#### Focal misalignment

***Recommendation: reject***

![](imgs/Fig5.1.png){width=100}![](imgs/Fig5.2.png){width=99}

*(In this case, mild misalignment results in focal irregularity of the cardiac morphology)*

#### Diffuse misalignment

***Recommendation: reject***

![](imgs/Fig6.1_2.png){width=100}![](imgs/Fig6.2.png){width=100}

## Flat apex

- When generating the mesh, the apical endocardium is typically near the superior margin of the final slice, whereas the epicardium is generally near the inferior margin of the final slice
- There are slight differences in mesh generation depending on whether the final slice are all myocardium or contains part of cavity
- If the final slice is relatively small, it may be ignored during mesh generation.

![](imgs/Fig7.1.png){width=100}![](imgs/Fig7.2.png){width=110}

Evaluate whether the cardiac apex is sharp based on the mesh generation pattern.

***Recommendation: accept the first mesh, reject the second mesh***

![](imgs/Fig8.1.png){width=100}![](imgs/Fig8.2.png){width=100}

*(Sharp apex vs. flat apex)*

## Special cases

***Recommendation: reject***

![](imgs/Fig9.1.png){width=100}![](imgs/Fig2.png){width=100}

*(When scanning, the short-axis plane was not perpendicular to the long axis, resulting in an irregular overall morphology)*

***Recommendation: reject***

![](imgs/Fig10.1.png){width=100}![](imgs/Fig10.2.png){width=100}

*(All slices are displaced simultaneously toward one side)*

***Recommendation: reject***

![](imgs/Fig11.1.png){width=100}![](imgs/Fig11.2.png){width=100}

*(Insufficient apical repair resulted in an overall shorter and smaller heart)*

## Good cases

***Recommendation: accept***

![](imgs/Fig13.1.png){width=100}![](imgs/Fig13.2.png){width=90}

***Recommendation: accept***

![](imgs/Fig12.1.png){width=100}![](imgs/Fig12.2.png){width=95}