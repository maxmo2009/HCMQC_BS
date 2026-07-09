# hulei — ACDC QC 边界病例报告

> 数据集: `sabotaged_acdc / seed42_ratio0.5_shift5` · 共 150 例,hulei 已全部完成 QC。
> 本报告收录 **全部 48 个边界 (patient, phase)** —— 即评论里有犹豫措辞("勉强接受/先接受/讨论/再对比/想想还是…")的所有条目。

> 其中 **16 个标记为 ⚑必须讨论**(她明确写了"讨论 / 问师兄"),正文里用红色 **⚑【必须讨论】** 标出。

> 每个病例给出**两个侧面视图**(冠状面 Coronal + 矢状面 Sagittal),
> 沿心脏长轴从**基底部 → 心尖部**剖开 —— 这是层间错位 / 心尖缺层最容易看出来的方向。
> 颜色: <span style="color:red">■</span> LV(红) · <span style="color:#0f0">■</span> RV(绿) · <span style="color:#08f">■</span> 心肌 Myo(蓝),半透明叠加在灰度 MRI 上。

> 生成于本地,图片为患者数据衍生 —— `reports/` 已加入 `.gitignore`,请勿提交。

---

**小结**: 48 个边界条目中 39 暂定 Accept、9 暂定 Reject;**16 个必须讨论**。高频主题: 心尖部缺层 / 未识别、中间部个别层移位。明确 action item: **patient136 ES — 她写了"问一下许可师兄"**。

**⚑ 必须讨论的 16 个**: patient009 ED · patient009 ES · patient025 ED · patient026 ES · patient028 ED · patient028 ES · patient039 ES · patient042 ES · patient049 ES · patient051 ES · patient056 ES · patient061 ED · patient062 ED · patient136 ES · patient147 ES · patient149 ED

---

## 1. patient004 · ED · ✅ Accept

> hulei: *整体效果较好，心尖部最后一层再往中间对齐就好了*

![patient004 ED](imgs/patient004_ED.png)

---

## 2. ⚑ <span style="color:#c00">【必须讨论】</span> patient009 · ED · ✅ Accept

> hulei: *先接受吧，但是需要再讨论一下，因为整体都很好，但感觉心尖部少了一层*

![patient009 ED](imgs/patient009_ED.png)

---

## 3. ⚑ <span style="color:#c00">【必须讨论】</span> patient009 · ES · ✅ Accept

> hulei: *先接受吧，但是需要再讨论一下，因为整体都很好，但感觉心尖部少了一层*

![patient009 ES](imgs/patient009_ES.png)

---

## 4. patient010 · ED · ❌ Reject

> hulei: *中间部有一层移位明显，心尖部最后一层可以再调整一下位置*

![patient010 ED](imgs/patient010_ED.png)

---

## 5. patient011 · ED · ✅ Accept

> hulei: *先接受，整体效果较好，心尖部感觉少一层*

![patient011 ED](imgs/patient011_ED.png)

---

## 6. patient011 · ES · ✅ Accept

> hulei: *先接受，整体效果较好，心尖部感觉少一层*

![patient011 ES](imgs/patient011_ES.png)

---

## 7. patient015 · ED · ✅ Accept

> hulei: *要是心尖部最后一层往中间移一点就完美了*

![patient015 ED](imgs/patient015_ED.png)

---

## 8. patient015 · ES · ✅ Accept

> hulei: *同ED期，心尖部最后一层往中间移一点就完美了*

![patient015 ES](imgs/patient015_ES.png)

---

## 9. patient019 · ED · ✅ Accept

> hulei: *个别层稍有移位，勉强接受*

![patient019 ED](imgs/patient019_ED.png)

---

## 10. patient020 · ES · ❌ Reject

> hulei: *中间部有一层移位稍明显，想想还是算了*

![patient020 ES](imgs/patient020_ES.png)

---

## 11. ⚑ <span style="color:#c00">【必须讨论】</span> patient025 · ED · ✅ Accept

> hulei: *需要讨论一下，心尖部感觉还是少了一点，但其他都很好*

![patient025 ED](imgs/patient025_ED.png)

---

## 12. patient026 · ED · ✅ Accept

> hulei: *心尖部稍有移位，勉强接受吧*

![patient026 ED](imgs/patient026_ED.png)

---

## 13. ⚑ <span style="color:#c00">【必须讨论】</span> patient026 · ES · ❌ Reject

> hulei: *可以讨论一下，基底部第一层移位稍明显，其它层比较好*

![patient026 ES](imgs/patient026_ES.png)

---

## 14. ⚑ <span style="color:#c00">【必须讨论】</span> patient028 · ED · ✅ Accept

> hulei: *先接受，但是需要讨论一下，心尖部最下面一层扫到了但是没有识别*

![patient028 ED](imgs/patient028_ED.png)

---

## 15. ⚑ <span style="color:#c00">【必须讨论】</span> patient028 · ES · ✅ Accept

> hulei: *先接受，但是需要讨论一下，同ED，心尖部最后一层没有识别，心尖的形状不是很完整*

![patient028 ES](imgs/patient028_ES.png)

---

## 16. patient036 · ED · ✅ Accept

> hulei: *勉强可以接受*

![patient036 ED](imgs/patient036_ED.png)

---

## 17. patient038 · ES · ✅ Accept

> hulei: *勉强接受吧，虽然感觉心尖部还是少了一点*

![patient038 ES](imgs/patient038_ES.png)

---

## 18. ⚑ <span style="color:#c00">【必须讨论】</span> patient039 · ES · ❌ Reject

> hulei: *需要讨论一下，中间部2层有点移位，影响中间部的形状，先拒绝*

![patient039 ES](imgs/patient039_ES.png)

---

## 19. ⚑ <span style="color:#c00">【必须讨论】</span> patient042 · ES · ❌ Reject

> hulei: *中间部有1层移位较明显，先拒绝，但可以讨论一下*

![patient042 ES](imgs/patient042_ES.png)

---

## 20. patient048 · ES · ✅ Accept

> hulei: *勉强可以接受*

![patient048 ES](imgs/patient048_ES.png)

---

## 21. ⚑ <span style="color:#c00">【必须讨论】</span> patient049 · ES · ❌ Reject

> hulei: *讨论一下吧，心尖部感觉还是可以再扫一层的*

![patient049 ES](imgs/patient049_ES.png)

---

## 22. patient050 · ED · ✅ Accept

> hulei: *勉强可以接受*

![patient050 ED](imgs/patient050_ED.png)

---

## 23. ⚑ <span style="color:#c00">【必须讨论】</span> patient051 · ES · ✅ Accept

> hulei: *心尖部整体有偏移，再讨论一下*

![patient051 ES](imgs/patient051_ES.png)

---

## 24. patient052 · ED · ✅ Accept

> hulei: *勉强可以接受*

![patient052 ED](imgs/patient052_ED.png)

---

## 25. patient055 · ES · ✅ Accept

> hulei: *勉强接受*

![patient055 ES](imgs/patient055_ES.png)

---

## 26. ⚑ <span style="color:#c00">【必须讨论】</span> patient056 · ES · ✅ Accept

> hulei: *勉强可以接受，再讨论一下*

![patient056 ES](imgs/patient056_ES.png)

---

## 27. patient059 · ES · ✅ Accept

> hulei: *勉强可以接受*

![patient059 ES](imgs/patient059_ES.png)

---

## 28. ⚑ <span style="color:#c00">【必须讨论】</span> patient061 · ED · ✅ Accept

> hulei: *先接受吧，感觉心尖部全是心肌的那一层没有识别上，讨论一下*

![patient061 ED](imgs/patient061_ED.png)

---

## 29. ⚑ <span style="color:#c00">【必须讨论】</span> patient062 · ED · ❌ Reject

> hulei: *有2层移位稍明显，暂不接受，不过可以讨论一下*

![patient062 ED](imgs/patient062_ED.png)

---

## 30. patient064 · ES · ✅ Accept

> hulei: *基底部有一层稍微有点移位，勉强接受吧*

![patient064 ES](imgs/patient064_ES.png)

---

## 31. patient072 · ES · ✅ Accept

> hulei: *基底部稍有移位，但勉强接受*

![patient072 ES](imgs/patient072_ES.png)

---

## 32. patient073 · ES · ✅ Accept

> hulei: *中间部有一层稍移位，先接受，后面再对比考虑一下*

![patient073 ES](imgs/patient073_ES.png)

---

## 33. patient091 · ED · ✅ Accept

> hulei: *基底部有一层移位稍明显了，先接受，后面再对比考虑一下*

![patient091 ED](imgs/patient091_ED.png)

---

## 34. patient100 · ED · ✅ Accept

> hulei: *先接受，心尖部再有一层就完美了，注意和之前类似的情况对比一下*

![patient100 ED](imgs/patient100_ED.png)

---

## 35. patient105 · ED · ✅ Accept

> hulei: *也是勉强接受*

![patient105 ED](imgs/patient105_ED.png)

---

## 36. patient105 · ES · ✅ Accept

> hulei: *基底部有点移位，先勉强接受吧*

![patient105 ES](imgs/patient105_ES.png)

---

## 37. patient107 · ES · ✅ Accept

> hulei: *基底部第一层有移位，但是整体可以勉强接受*

![patient107 ES](imgs/patient107_ES.png)

---

## 38. patient114 · ES · ✅ Accept

> hulei: *整体效果勉强可以接受*

![patient114 ES](imgs/patient114_ES.png)

---

## 39. patient122 · ED · ✅ Accept

> hulei: *只能说勉强接受了*

![patient122 ED](imgs/patient122_ED.png)

---

## 40. patient128 · ES · ✅ Accept

> hulei: *先接受吧，心尖部就少了一点点*

![patient128 ES](imgs/patient128_ES.png)

---

## 41. patient132 · ES · ✅ Accept

> hulei: *心尖部这个怎么说呢，先勉强接受吧*

![patient132 ES](imgs/patient132_ES.png)

---

## 42. ⚑ <span style="color:#c00">【必须讨论】</span> patient136 · ES · ✅ Accept

> hulei: *勉强可以接受吧，这种情况问一下许可师兄*

![patient136 ES](imgs/patient136_ES.png)

---

## 43. patient137 · ED · ✅ Accept

> hulei: *心尖部就差一点点，先勉强接受，再思考一下*

![patient137 ED](imgs/patient137_ED.png)

---

## 44. ⚑ <span style="color:#c00">【必须讨论】</span> patient147 · ES · ❌ Reject

> hulei: *薄层，就一层移位明显，先拒绝，后面讨论一下*

![patient147 ES](imgs/patient147_ES.png)

---

## 45. patient148 · ED · ✅ Accept

> hulei: *勉强可以接受吧*

![patient148 ED](imgs/patient148_ED.png)

---

## 46. patient148 · ES · ✅ Accept

> hulei: *也是勉强接受*

![patient148 ES](imgs/patient148_ES.png)

---

## 47. ⚑ <span style="color:#c00">【必须讨论】</span> patient149 · ED · ❌ Reject

> hulei: *整体效果不太想接受，再讨论考虑一下*

![patient149 ED](imgs/patient149_ED.png)

---

## 48. patient150 · ED · ✅ Accept

> hulei: *基底部第一层移位有点明显，但勉强可以接受吧*

![patient150 ED](imgs/patient150_ED.png)

---
