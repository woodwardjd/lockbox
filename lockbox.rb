#!/usr/bin/env ruby

require 'directory_watcher'
require 'fileutils'
require 'gpgr'

encrypted_dir = File.expand_path('~/Dropbox/Lockbox')
clear_dir = File.expand_path('~/Lockbox')

dw_priv = DirectoryWatcher.new encrypted_dir, :pre_load => true, :scanner => :coolio
dw_priv.interval = 1
dw_priv.stable = 3
dw_priv.add_observer do |*args| 
  args.each do |event| 
    if event.type == :stable
      puts event
    elsif event.type == :removed
      puts event
    end
  end
end


dw = DirectoryWatcher.new clear_dir, :pre_load => true, :scanner => :coolio
dw.interval = 1
dw.stable = 3
dw.add_observer do |*args| 
  args.each do |event| 
    puts event
    if event.type == :stable
      puts "   making " + File.dirname(event.path).sub(clear_dir,encrypted_dir)
      FileUtils.mkdir_p File.dirname(event.path).sub(clear_dir,encrypted_dir)
      #puts "   copying" 
      #FileUtils.cp event.path, File.dirname(event.path).sub(clear_dir,encrypted_dir)
      puts "   encrypting"
      Gpgr::Encrypt.file(event.path, :to => event.path.sub(clear_dir,encrypted_dir)).encrypt_using ['jason@jwoodward.com']
      puts "   work done."
    elsif event.type == :removed
      FileUtils.rm event.path.sub(clear_dir,encrypted_dir)
      puts "   work done."
    end
  end
end

puts "starting dw..."
dw.start
puts " done.  starting dw_priv..."
dw_priv.start
puts " done."
gets
dw.stop
dw_priv.stop
