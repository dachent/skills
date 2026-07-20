using System.Buffers.Binary;
using System.Text;
using XlsxWinContracts;

namespace XlsxWinSupervisor.Tests;

public class FramedControlTests
{
    [Fact]
    public void Round_trip_preserves_exact_excel_identity()
    {
        var expected = new ExcelProcessIdentity
        {
            ExcelPid = 1234,
            Hwnd = 987654,
            CreationTimeUtcFileTime = 112233,
            ImagePath = @"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
            SessionId = 2,
            User = @"DOMAIN\user",
        };
        using var stream = new MemoryStream();

        FramedControl.Write(stream, expected);
        stream.Position = 0;
        var observed = FramedControl.Read<ExcelProcessIdentity>(stream);

        Assert.Equal(expected.ExcelPid, observed.ExcelPid);
        Assert.Equal(expected.Hwnd, observed.Hwnd);
        Assert.Equal(expected.CreationTimeUtcFileTime, observed.CreationTimeUtcFileTime);
        Assert.Equal(expected.ImagePath, observed.ImagePath);
        Assert.Equal(expected.SessionId, observed.SessionId);
        Assert.Equal(expected.User, observed.User);
    }

    [Fact]
    public void Read_rejects_a_partial_header() =>
        Assert.Throws<EndOfStreamException>(() => FramedControl.Read<ContainmentAck>(new MemoryStream(new byte[] { 1, 0 })));

    [Fact]
    public void Read_rejects_a_partial_payload()
    {
        var frame = new byte[6];
        BinaryPrimitives.WriteInt32LittleEndian(frame.AsSpan(0, 4), 10);
        Assert.Throws<EndOfStreamException>(() => FramedControl.Read<ContainmentAck>(new MemoryStream(frame)));
    }

    [Theory]
    [InlineData(0)]
    [InlineData(-1)]
    [InlineData(65537)]
    public void Read_rejects_an_out_of_range_length(int length)
    {
        var frame = new byte[4];
        BinaryPrimitives.WriteInt32LittleEndian(frame, length);
        Assert.Throws<InvalidDataException>(() => FramedControl.Read<ContainmentAck>(new MemoryStream(frame)));
    }

    [Fact]
    public void Read_rejects_malformed_json()
    {
        var payload = Encoding.UTF8.GetBytes("not-json");
        var frame = new byte[4 + payload.Length];
        BinaryPrimitives.WriteInt32LittleEndian(frame.AsSpan(0, 4), payload.Length);
        payload.CopyTo(frame.AsSpan(4));
        Assert.ThrowsAny<Exception>(() => FramedControl.Read<ContainmentAck>(new MemoryStream(frame)));
    }
}
