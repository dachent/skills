using System.Buffers.Binary;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace XlsxWinContracts;

public sealed class ExcelProcessIdentity
{
    [JsonPropertyName("excel_pid")]
    public int ExcelPid { get; set; }
    [JsonPropertyName("hwnd")]
    public long Hwnd { get; set; }
    [JsonPropertyName("creation_time_utc_filetime")]
    public long CreationTimeUtcFileTime { get; set; }
    [JsonPropertyName("image_path")]
    public string ImagePath { get; set; } = "";
    [JsonPropertyName("session_id")]
    public int SessionId { get; set; }
    [JsonPropertyName("user")]
    public string User { get; set; } = "";
}

public sealed class ContainmentAck
{
    [JsonPropertyName("accepted")]
    public bool Accepted { get; set; }
    [JsonPropertyName("message")]
    public string Message { get; set; } = "";
}

public static class FramedControl
{
    private const int MaximumFrameBytes = 64 * 1024;

    public static void Write<T>(Stream stream, T value)
    {
        var payload = JsonSerializer.SerializeToUtf8Bytes(value, JsonDefaults.Options);
        if (payload.Length is <= 0 or > MaximumFrameBytes)
            throw new InvalidDataException($"Control frame length {payload.Length} is outside 1..{MaximumFrameBytes}.");
        Span<byte> header = stackalloc byte[4];
        BinaryPrimitives.WriteInt32LittleEndian(header, payload.Length);
        stream.Write(header);
        stream.Write(payload);
        stream.Flush();
    }

    public static T Read<T>(Stream stream)
    {
        Span<byte> header = stackalloc byte[4];
        ReadExactly(stream, header);
        var length = BinaryPrimitives.ReadInt32LittleEndian(header);
        if (length is <= 0 or > MaximumFrameBytes)
            throw new InvalidDataException($"Control frame length {length} is outside 1..{MaximumFrameBytes}.");
        var payload = new byte[length];
        ReadExactly(stream, payload);
        return JsonSerializer.Deserialize<T>(payload, JsonDefaults.Options)
            ?? throw new InvalidDataException("Control frame deserialized to null.");
    }

    private static void ReadExactly(Stream stream, Span<byte> buffer)
    {
        var offset = 0;
        while (offset < buffer.Length)
        {
            var read = stream.Read(buffer[offset..]);
            if (read == 0) throw new EndOfStreamException("Control channel ended mid-frame.");
            offset += read;
        }
    }
}
