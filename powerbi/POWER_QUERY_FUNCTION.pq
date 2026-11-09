// Optional Power Query helper named fxLoadProjectCSV
// Create a blank query, open Advanced Editor, paste this code and name it fxLoadProjectCSV.
// Set output folder to the extracted <project>/outputs path on your own machine.
(FileName as text, OutputFolder as text) as table =>
let
    FilePath = OutputFolder & "\\" & FileName,
    Source = Csv.Document(File.Contents(FilePath), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(PromotedHeaders, {})
in
    Typed
