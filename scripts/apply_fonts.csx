/// <summary>
/// Apply Korean font textures and glyph tables to data.win.
/// Creates new EmbeddedTexture entries, replaces font glyphs.
/// Uses independent TexData objects (not shared with originals).
///
/// Usage: UndertaleModCli load backup/data.win -s scripts/apply_fonts.csx -o out/data.win
/// </summary>
using System;
using System.Linq;
using System.IO;
using UndertaleModLib.Models;
using UndertaleModLib.Util;

EnsureDataLoaded();

string baseDir = System.GetEnv("JETLANCER_BASE");
if (baseDir == null) baseDir = ".";

void applyFont(string fontName, string texPngPath, string glyphCsvPath)
{
    Console.WriteLine("== Applying: " + fontName + " ==");
    
    var font = Data.Fonts.FirstOrDefault(f => f.Name.Content == fontName);
    if (font == null) { Console.WriteLine("  Font not found!"); return; }
    Console.WriteLine("  Original: " + font.Glyphs.Count + " glyphs, texPage=" + 
        Data.EmbeddedTextures.IndexOf(font.Texture.TexturePage));

    // Load the new texture PNG
    Console.WriteLine("  Loading texture: " + texPngPath);
    var pngBytes = File.ReadAllBytes(texPngPath);
    var newImg = GMImage.FromPng(pngBytes);
    Console.WriteLine("  New texture size: " + newImg.Width + "x" + newImg.Height);

    // Create new EmbeddedTexture with its OWN TexData
    var newET = new UndertaleEmbeddedTexture();
    // newET already has a TexData (automatic), but Image is null
    newET.TextureData.Image = newImg;       // set the image on the new ET's own TexData
    Data.EmbeddedTextures.Add(newET);
    int newTexIdx = Data.EmbeddedTextures.Count - 1;
    Console.WriteLine("  New EmbeddedTexture at index " + newTexIdx);

    // Reuse the existing TexturePageItem (to avoid orphan page-item issues),
    // but point it to our new EmbeddedTexture
    var pti = font.Texture;
    pti.SourceX = (ushort)0;
    pti.SourceY = (ushort)0;
    pti.SourceWidth = (ushort)newImg.Width;
    pti.SourceHeight = (ushort)newImg.Height;
    pti.TargetX = 0;
    pti.TargetY = 0;
    pti.TargetWidth = (ushort)newImg.Width;
    pti.TargetHeight = (ushort)newImg.Height;
    pti.TexturePage = newET;

    // Read glyph CSV
    var csvContent = File.ReadAllText(glyphCsvPath);
    var lines = csvContent.Split("\n");
    Console.WriteLine("  Glyph map lines: " + lines.Length);

    // Clear old glyphs and populate new ones
    font.Glyphs.Clear();
    int count = 0;
    int errors = 0;

    for (int i = 1; i < lines.Length; i++)
    {
        string line = lines[i].Trim();
        if (line.Length == 0) continue;

        // Split by comma or semicolon
        var parts = line.Contains(",") ? line.Split(",") : line.Split(";");
        if (parts.Length < 7) { errors++; continue; }

        try
        {
            int charCode = int.Parse(parts[0].Trim());
            int srcX = int.Parse(parts[1].Trim());
            int srcY = int.Parse(parts[2].Trim());
            int srcW = int.Parse(parts[3].Trim());
            int srcH = int.Parse(parts[4].Trim());
            int shift = int.Parse(parts[5].Trim());
            int offset = int.Parse(parts[6].Trim());

            var g = new UndertaleFont.Glyph();
            g.Character = (char)charCode;
            g.SourceX = (ushort)srcX;
            g.SourceY = (ushort)srcY;
            g.SourceWidth = (ushort)srcW;
            g.SourceHeight = (ushort)srcH;
            g.Shift = (short)shift;
            g.Offset = (short)offset;
            font.Glyphs.Add(g);
            count++;
        }
        catch (Exception ex)
        {
            errors++;
            if (errors <= 3)
                Console.WriteLine("  Parse error line " + (i+1) + ": " + ex.Message);
        }
    }
    Console.WriteLine("  Added " + count + " glyphs (" + errors + " errors)");

    Console.WriteLine("  Font texture updated");
}

// ── Apply ──
applyFont("fo_text_jap",
    baseDir + "/fonts/tex_text.png",
    baseDir + "/fonts/glyphs_text.csv");

applyFont("fo_header_jap",
    baseDir + "/fonts/tex_header.png",
    baseDir + "/fonts/glyphs_header.csv");

// Chinese fonts use same small layout; skip for now
// applyFont("fo_text_chinese", ...);
// applyFont("fo_header_chinese", ...);

// ── Verification ──
Console.WriteLine("\n== Verification ==");

void verifyFont(string fontName)
{
    var font = Data.Fonts.FirstOrDefault(f => f.Name.Content == fontName);
    if (font == null) { Console.WriteLine("NOT FOUND: " + fontName); return; }

    int hangul = 0, jamo = 0, latin = 0;
    foreach (var g in font.Glyphs)
    {
        int cp = (int)g.Character;
        if (cp >= 0xAC00 && cp <= 0xD7A3) hangul++;
        else if (cp >= 0x3131 && cp <= 0x318E) jamo++;
        else if ((cp >= 0x20 && cp <= 0x7F) || (cp >= 0xA0 && cp <= 0xFF)) latin++;
    }
    var pti = font.Texture;
    int texi = Data.EmbeddedTextures.IndexOf(pti.TexturePage);
    Console.WriteLine(fontName + ": total=" + font.Glyphs.Count +
        " latin=" + latin + " hangul_syllables=" + hangul + " jamo=" + jamo +
        " texIdx=" + texi + " texSize=" + pti.SourceWidth + "x" + pti.SourceHeight);
}

verifyFont("fo_text_jap");
verifyFont("fo_header_jap");

Console.WriteLine("\nScript done. Save with: -o out/data.win");