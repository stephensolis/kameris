#!wolframscript -script

(* plot settings *)

colorScheme = {
	Blue, Red, Green, Magenta, Orange, Darker@Green, Cyan, Brown, Purple, Yellow
};


(* functions *)

(* MDS points scaled to (-1, 1) *)
scaledPoints[pts_] := (
	Transpose[Rescale[#, {Min[#], Max[#]}, {-1, 1}]& /@ Transpose[pts]]
);

(* taxaNames, taxaIndexes split *)
metadataToGroups[metadata_] :=
	Module[{taxaNames, taxaIndexes},
		taxaNames = Union[("group" /. #)& /@ metadata];
		taxaIndexes = Flatten@Position[metadata, _?(MemberQ["group"->#]), 1]& /@ taxaNames;

		{taxaNames, taxaIndexes}
	];

(* plot options *)
plotLegendAndStyle[taxaNames_, taxaIndexes_, colors_] :=
	Module[{legendNames, legend, plotStyle},
		(*legend*)
		legendNames = StringForm["`` (``)", #1, #2]& @@@ Transpose[{taxaNames, Length /@ taxaIndexes}];
		legend = SwatchLegend[colors, legendNames];

		(*plot style*)
		plotStyle = Directive[#, PointSize[0.01]]& /@ colors;

		{legend, plotStyle}
	];

(* drawing incorrect points *)
incorrectPoints[points_, incorrectIndexes_] :=
	Module[{incorrectPts},
		(*points*)
		incorrectPts = points[[incorrectIndexes]];

		(*0.0001 is to fix a clipping issue with Graphics3D*)
		{Opacity[.35], Orange, PointSize[0.022], Point[incorrectPts+0.0001]}
	];

(* 2D scatterplot *)
generate2DPlot[longPoints_, metadata_, taxaIndexes_, incorrectIndexes_, legend_, plotStyle_] :=
	Module[{points, ptsForPlot},
		(*take 2 dimensions*)
		points = Take[#, 2]& /@ longPoints;

		(*create point annotations (for mouseover info)*)
		pointAnnotations = MapIndexed[(
			Annotation[Point[points[[#]]], metadata[[#]], "Mouse"]
		)&, taxaIndexes, {2}];

		(*separate points into groups*)
		ptsForPlot = Map[points[[#]]&, taxaIndexes, {2}];

		(*plot*)
		Show[
			ListPlot[ptsForPlot, PlotStyle->plotStyle, PlotRange->{{-1.1, 1.1}, {-1.1, 1.1}},
					 PlotLegends->legend, AspectRatio->1, Frame->True],
			Graphics[incorrectPoints[points, incorrectIndexes]],
			Graphics[{Opacity[0], PointSize[0.022], pointAnnotations}]
		]
	];

(* 3D scatterplot *)
generate3DPlot[longPoints_, metadata_, taxaIndexes_, incorrectIndexes_, legend_, plotStyle_] :=
	Module[{points, pointAnnotations, ptsForPlot},
		(*take 3 dimensions*)
		points = Take[#, 3]& /@ longPoints;

		(*create point annotations (for mouseover info)*)
		pointAnnotations = MapIndexed[(
			Annotation[Text["", points[[#]]], metadata[[#]], "Mouse"]
		)&, taxaIndexes, {2}];

		(*separate points into groups*)
		ptsForPlot = Map[points[[#]]&, taxaIndexes, {2}];

		(*plot*)
		Show[
			ListPointPlot3D[ptsForPlot, PlotStyle->plotStyle, PlotRange->{{-1.1, 1.1}, {-1.1, 1.1}, {-1.1, 1.1}},
							PlotLegends->legend, AspectRatio->1, BoxRatios->{1, 1, 1}],
			Graphics3D[incorrectPoints[points, incorrectIndexes]],
			Graphics3D[pointAnnotations]
		]
	];

(* mouseover info grid *)
mouseoverInfoGrid[] :=
	Module[{currPtData, labels, tableData},
		Dynamic[
			currPtData = MouseAnnotation[];

			If[!Null === currPtData,
				labels = Style[First@#, Bold]& /@ currPtData;
				tableData = Transpose[{labels, #[[2]]& /@ currPtData}];
			];

			Grid[tableData, Alignment->Left, ItemSize->{{Scaled[.2], Scaled[.8]}}, Frame->All]
		]
	];


(* load data *)

If[Length[$ScriptCommandLine] != 2,
	Print["usage: make_plots.ws <settings (base64d JSON)>"];
	Exit[1];
];

settings = ImportString[$ScriptCommandLine[[2]], {"Base64", "JSON"}];
points = Import["mds_file" /. settings];
metadata = Import["metadata_file" /. settings];

If[MemberQ[Keys[settings], "classifier_name"],
	classificationData = (("classifier_name" /. settings) /. Import["classification_file" /. settings]);

	incorrectIndexes = ("misclassified_indexes" /. (("accuracy_type" /. settings) /. classificationData)) + 1;
	metadata = Join[metadata, {"misclassified"->MemberQ[incorrectIndexes, #]}& /@ Range[Length@metadata], 2];
,
	incorrectIndexes = {};
];

(* make and export plots *)

points = scaledPoints[points];
{taxaNames, taxaIndexes} = metadataToGroups[metadata];

colors = Take[colorScheme, Length@taxaNames];
{legend, plotStyle} = plotLegendAndStyle[taxaNames, taxaIndexes, colors];

plots = {
	generate2DPlot[points, metadata, taxaIndexes, incorrectIndexes, legend, plotStyle],
	generate3DPlot[points, metadata, taxaIndexes, incorrectIndexes, legend, plotStyle],
	mouseoverInfoGrid[]
};

Export["output_file" /. settings, Notebook[Cell@*BoxForm@*MakeBoxes /@ plots], "NB"];
If[MemberQ[Keys[settings], "svg_output_file"],
	Export["svg_output_file" /. settings, plots[[1]], "SVG"];
];
If[MemberQ[Keys[settings], "png_output_file"],
	Export["png_output_file" /. settings, plots[[1]], "PNG", ImageResolution->300];
];
